"""Full-text binary classification, traceable transport, source gates and OR panel.

All new artifacts are isolated in the user-requested v2 run bundle. No acquisition,
extraction, old-label reuse or human-decision write occurs here.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
import threading
import uuid
from functools import lru_cache
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from . import item1a_semantic as prior
from .item7_governance import identity, quote_location
from .llm import governance_v2_prompt as prompt
from .llm.client import MODEL, INTENDED_MODEL_VERSION, build_payload, chat_json, load_config

ROOT = prior.ROOT
OUT = ROOT / 'outputs/full_universe_implemented_internal_ai_governance_v2'
STANDARD = ROOT / 'docs/implemented_internal_ai_governance_v2.md'
A = ROOT / 'data/interim/documents/full_universe_item1a_manifest.csv'
B = ROOT / 'data/interim/documents/full_universe_item7/optimization_v2/manifest_item7-secondary-v2.4.csv'
SECONDARY = ROOT / 'outputs/full_universe_item1a/secondary_qa/secondary_qa_results.csv'
REPAIRS = ROOT / 'data/interim/documents/item1a_review_repair_20260930_v3/comparison.csv'
BASELINE = ROOT / 'data/interim/classifications/full_universe_item7_implemented_internal_ai_governance/v1/run_manifest.json'
MAX_TOKENS = 16384
VALIDATION_REQUEST_LIMIT = 2


def now():
    return datetime.now(timezone.utc).isoformat()


def log(message):
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    print(message,flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'execution.log').open('a',encoding='utf-8') as f:
        f.write(now()+' '+str(message)+'\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def rows(path, values, fields=None):
    fields = fields or list(values[0]) if values else fields or ['cik', 'ticker', 'fiscal_year', 'reason']
    tmp = path.with_suffix('.csv.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(values)
    tmp.replace(path)


@lru_cache(maxsize=1)
def system():
    return prompt.SYSTEM_PREFIX + STANDARD.read_text(encoding='utf-8-sig') + prompt.SYSTEM_SUFFIX


def user(row, text):
    return prompt.USER_TEMPLATE.format(**row, full_text=text)


def key(row):
    return (*identity(row), row['section'])


def texts(row):
    data = (ROOT / row['input_file']).read_bytes()
    if sha(data) != row['input_sha256']:
        raise ValueError('Source hash changed')
    return data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')


def source_gate(r, section, secondary, newer):
    path = r.get(section + '_path', '')
    digest = r.get(section + '_sha256', '')
    basis = r.get('quality_status', '')
    reason = ''
    if r['extraction_status'] != 'success':
        reason = 'extraction_' + (r['extraction_status'] or 'not_acquired')
    elif section == 'item7' and basis != 'automatic_pass':
        reason = 'unresolved_extraction_quality'
    elif section == 'item1a':
        s = secondary.get(identity(r), {})
        n = newer.get(identity(r), {})
        if n:
            if n['accession_number'] != r['accession_number'] or n['old_item1a_sha256'] != digest:
                reason = 'repair_provenance_mismatch'
            elif n['new_extraction_status'] in {'auto_verified', 'human_accepted_original'} and not n['remaining_review_reason']:
                basis = 'latest_original_verified'
            elif n['human_judgment'] == '提取正确，可以接受' and n['old_item1a_sha256'] == digest:
                # Filing-selection doubts remain unresolved even if extraction is accepted.
                reason = 'filing_selection_unresolved' if n['remaining_review_reason'] else ''
                basis = 'human_accepted_original'
            else:
                reason = 'latest_review_unresolved:' + n['new_extraction_status'] + ':' + n['remaining_review_reason']
            if n['extraction_class'] == 'incorporation_external_reference':
                reason = 'external_incorporated_text_unavailable'
        elif s:
            if s['accession_number'] != r['accession_number'] or s['item1a_sha256'] != digest:
                reason = 'secondary_provenance_mismatch'
            elif s['secondary_status'] == 'auto_verified':
                basis = 'secondary_original_verified'
            elif s['secondary_status'] == 'repaired_verified' and s['repair_path'] and s['repair_sha256']:
                path, digest, basis = s['repair_path'], s['repair_sha256'], 'secondary_verified_saved_repair'
            else:
                reason = 'secondary_review_unresolved:' + s['secondary_status']
        elif basis != 'automatic_pass':
            reason = 'unresolved_extraction_quality'
    if not r['cik'] and not reason:
        reason = 'unresolved_company_identity'
    if not r['accession_number'] and not reason:
        reason = 'missing_accession'
    available = False
    chars = 0
    if not reason:
        try:
            data = (ROOT / path).read_bytes()
            if not digest or sha(data) != digest:
                raise ValueError('input_hash_mismatch')
            text = data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
            chars = len(text)
            if not text.strip():
                raise ValueError('empty_text')
            # A correct extracted pointer is insufficient to observe incorporated risk factors.
            if len(text) < 2000 and re.search(r'(?i)incorporat\w*.{0,100}(reference|herein)|see.{0,50}(annual report|form 10-k)', text, re.S):
                raise ValueError('external_incorporated_text_unavailable')
            available = True
        except (OSError, UnicodeError, ValueError) as e:
            reason = str(e) if isinstance(e, ValueError) else type(e).__name__
    return dict(input_file=path, input_sha256=digest, text_available=available,
                source_status='observed' if available else 'unavailable_valid_text',
                source_reason=reason, quality_basis=basis, text_characters=chars,
                original_input_file=r.get(section+'_path', ''), original_input_sha256=r.get(section+'_sha256', ''),
                extraction_status=r['extraction_status'], extraction_review_reason=r.get('review_reason', ''))


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [A, B, SECONDARY, REPAIRS, STANDARD, BASELINE]
    frozen = {rel(p): sha(p.read_bytes()) for p in sources}
    config = dict(provider='DeepSeek', model=MODEL, intended_model_version=INTENDED_MODEL_VERSION,
                  temperature=0, max_tokens=MAX_TOKENS, response_format={'type':'json_object'},
                  base_url='https://api.deepseek.com', endpoint='/chat/completions', timeout_seconds=120,
                  max_retries=3, retry_backoff_seconds=[2,4,8], validation_request_limit=VALIDATION_REQUEST_LIMIT,
                  context_limit=1000000, settings_source=rel(BASELINE), settings_source_sha256=frozen[rel(BASELINE)],
                  full_text_input=True, keyword_screening=False, cost=None, cost_basis='No verified pricing snapshot available',
                  prompt_version=prompt.PROMPT_VERSION)
    meta = dict(prompt_version=prompt.PROMPT_VERSION, inputs=frozen, system_sha256=sha(system().encode()),
                user_template_sha256=sha(prompt.USER_TEMPLATE.encode()), llm_config=config,
                code_hashes={rel(p):sha(p.read_bytes()) for p in [Path(__file__),ROOT/'src/ai_restrictions/llm/governance_v2_prompt.py',ROOT/'src/ai_restrictions/llm/client.py']},
                merge_basis='User task section 5.1: observed-section estimator; single-section Negative permitted',
                status='prepared', started_at_utc=now())
    oldpath = OUT/'run_manifest.json'
    if oldpath.exists():
        old = json.loads(oldpath.read_text(encoding='utf-8'))
        for k in ['inputs','system_sha256','user_template_sha256','llm_config']:
            if old[k] != meta[k]:
                raise ValueError('Resume configuration/input changed: '+k)
        return json.loads((OUT/'input_manifest.json').read_text(encoding='utf-8')), old
    a, b = read(A), read(B)
    for rs in [a,b]:
        if len({identity(r) for r in rs}) != len(rs):
            raise ValueError('Duplicate normalized company/year')
    by = {identity(r):r for r in b}
    if set(by) != {identity(r) for r in a}:
        raise ValueError('Section universe mismatch')
    secondary = {identity(r):r for r in read(SECONDARY)}
    newer = {identity(r):r for r in read(REPAIRS)}
    states, audit = [], []
    for r in a:
        other = by[identity(r)]
        if r['ticker'] != other['ticker'] or r['company_key'] != other['company_key']:
            raise ValueError('Company identity cross-section mismatch')
        for section, src in [('item1a',r),('item7',other)]:
            state = {k:src[k] for k in ['company_name','ticker','cik','fiscal_year','accession_number','filing_date']}
            state['cik'] = str(int(src['cik'])).zfill(10) if src['cik'] else ''
            state.update(section=section, fiscal_year_end=src['report_date'], accession_conflict=False, **source_gate(src,section,secondary,newer))
            if state['text_available']:
                payload = build_payload(system(), user(state, texts(state)), max_tokens=MAX_TOKENS)
                bound = len(json.dumps(payload, ensure_ascii=False).encode()) + MAX_TOKENS + 2048
                if bound >= 1000000:
                    state.update(text_available=False,source_status='unavailable_valid_text',source_reason='context_limit_exceeded')
                state['conservative_token_bound'] = bound
            else:
                state['conservative_token_bound'] = None
            states.append(state)
        if r['accession_number'] and other['accession_number'] and r['accession_number'] != other['accession_number']:
            audit.append(dict(cik=r['cik'], ticker=r['ticker'], fiscal_year=r['fiscal_year'],
                              item1a_accession=r['accession_number'], item7_accession=other['accession_number']))
            # Preserve a valid individual chapter but hold any cross-filing merge for review.
            for s in states[-2:]:
                s['accession_conflict'] = True
        if len(states)%2000 == 0:
            log(f'Source checks: {len(states)}/{2*len(a)}')
    rows(OUT/'accession_audit.csv',audit)
    rows(OUT/'input_manifest.csv',states)
    dump(OUT/'input_manifest.json',states)
    dump(OUT/'llm_config.json',config)
    (OUT/'system_prompt.txt').write_text(system(),encoding='utf-8')
    (OUT/'user_prompt_template.txt').write_text(prompt.USER_TEMPLATE,encoding='utf-8')
    (OUT/'classification_standard_snapshot.md').write_bytes(STANDARD.read_bytes())
    # Freeze all old classification artifacts, all selected text bytes and the source manifests.
    protected = dict(frozen)
    for directory in [ROOT/'outputs/full_universe_implemented_internal_ai_governance', ROOT/'data/interim/classifications/full_universe_item7_implemented_internal_ai_governance/v1']:
        for p in directory.rglob('*'):
            if p.is_file(): protected[rel(p)]=sha(p.read_bytes())
    for r in states:
        if r['input_file'] and (ROOT/r['input_file']).is_file():
            protected[r['input_file']]=sha((ROOT/r['input_file']).read_bytes())
    dump(OUT/'protected_integrity.json',protected)
    meta.update(target_firm_years=len(a),available_sections=dict(Counter(r['section'] for r in states if r['text_available'])),
                source_reason_counts=dict(Counter(r['source_reason'] for r in states if not r['text_available'])))
    dump(oldpath,meta)
    log(json.dumps({k:meta[k] for k in ['target_firm_years','available_sections']},ensure_ascii=False))
    return states,meta


FIELDS = {'classification','evidence','reason','manual_review_needed','review_reason','mechanism_summary','scope_limitation','temporal_basis'}


def validate(result, text):
    if not isinstance(result,dict) or set(result) != FIELDS:
        raise ValueError('JSON fields differ from v2 schema')
    if type(result['manual_review_needed']) is not bool:
        raise ValueError('Invalid review boolean')
    label = result['classification']
    if result['manual_review_needed']:
        if label is not None or not result['review_reason'].strip():
            raise ValueError('Material ambiguity must remain null with review reason')
    elif label not in {'Positive','Negative'}:
        raise ValueError('Invalid binary label')
    if not isinstance(result['evidence'],list) or any(not isinstance(q,str) or not q.strip() for q in result['evidence']):
        raise ValueError('Invalid evidence array')
    for f in FIELDS - {'classification','evidence','manual_review_needed'}:
        if not isinstance(result[f],str): raise ValueError('Invalid string: '+f)
    if not result['reason'].strip(): raise ValueError('Missing reason')
    locations = []
    for q in result['evidence']:
        loc = quote_location(text,q)
        if loc is None: raise ValueError('Evidence is not a contiguous source quote')
        locations.append(loc)
    if label == 'Positive' and (not locations or not result['mechanism_summary'].strip()):
        raise ValueError('Positive lacks locatable governance evidence')
    return locations


def request_payload(row):
    return build_payload(system(),user(row,texts(row)),max_tokens=MAX_TOKENS)


def cache_file(row):
    digest=row.get('request_payload_sha256') or sha(json.dumps(request_payload(row),ensure_ascii=False).encode())
    issuer = row['cik'] or row['ticker']
    return OUT/'cache'/f"{issuer}_{row['fiscal_year']}_{row['section']}_{digest}.json"


def execute(row, config, lock):
    base=dict(row, prompt_version=prompt.PROMPT_VERSION,model=MODEL)
    path=cache_file(row)
    if path.exists():
        saved=json.loads(path.read_text(encoding='utf-8'))
        if saved.get('status') in {'complete','review'}:
            validate(saved['result'],texts(row))
            return saved
    else: saved={}
    previous=int(saved.get('validation_requests',0))
    # HTTP 402 produces no model response and does not consume semantic-retry
    # budget; a funded resume must be able to retry the same saved source.
    if saved.get('error')=='RuntimeError: DeepSeek HTTP 402':
        previous=0
    if previous >= VALIDATION_REQUEST_LIMIT:
        return saved
    payload=request_payload(row)
    digest=sha(json.dumps(payload,ensure_ascii=False).encode())
    payloadpath=OUT/'requests'/f'{digest}.json'
    if not payloadpath.exists(): dump(payloadpath,payload)
    text=texts(row)
    for vtry in range(previous, VALIDATION_REQUEST_LIMIT):
        group=uuid.uuid4().hex
        active={'index':0,'raw':None}
        def observe(event):
            if event['status']=='started': active['index']=event['attempt']
            data={k:row[k] for k in ['cik','ticker','fiscal_year','section','input_file','input_sha256']}
            data.update(timestamp_utc=now(),request_id=f"{group}_{active['index']}",prompt_version=prompt.PROMPT_VERSION,
                        model=MODEL,messages_snapshot=rel(payloadpath),payload_sha256=digest,
                        validation_request=vtry,**event)
            if event['status']=='response_received':
                data['raw_response_file']=active['raw']
            with lock:
                with (OUT/'request_manifest.jsonl').open('a',encoding='utf-8') as f:
                    f.write(json.dumps(data,ensure_ascii=False)+'\n')
        def raw(response):
            rawpath=OUT/'responses'/f"{group}_{active['index']}.json"
            dump(rawpath,response)
            active['raw']=rel(rawpath)
        try:
            result,metadata=chat_json(payload['messages'][0]['content'],payload['messages'][1]['content'],
                                     config=config,max_tokens=MAX_TOKENS,attempt_observer=observe,response_observer=raw)
            observe({'status':'raw_saved','raw_response_file':active['raw']})
            locations=validate(result,text)
            if metadata['returned_model'].lower() not in {MODEL.lower(),INTENDED_MODEL_VERSION.lower()}:
                raise ValueError('Returned model differs from specified baseline')
            record=dict(base,result=result,metadata=metadata,quote_locations=locations,
                        status='review' if result['manual_review_needed'] else 'complete',
                        classified_at_utc=now(),payload_sha256=digest,messages_snapshot=rel(payloadpath),
                        raw_response_file=active['raw'],validation_requests=vtry+1)
            dump(path,record)
            observe({'status':'validated','classification_status':record['status'],'cache_file':rel(path)})
            return record
        except Exception as exc:
            error=f'{type(exc).__name__}: {exc}'
            record=dict(base,status='error',error=error,validation_requests=vtry+1,
                        payload_sha256=digest,messages_snapshot=rel(payloadpath),raw_response_file=active['raw'])
            if error=='RuntimeError: DeepSeek HTTP 402':
                record['validation_requests']=vtry
                record['provider_billing_blocked']=True
            dump(path,record)
            observe({'status':'validation_or_transport_error','error':error,'raw_response_file':active['raw']})
            # Transport already performs finite retries; avoid duplicating that policy.
            if isinstance(exc,RuntimeError): return record
    return record


def decision(a,b,conflict=False):
    if a == 'Positive' or b == 'Positive':
        return ('','review_accession_conflict') if conflict else ('1','complete')
    if a in {'pending','error','review'} or b in {'pending','error','review'}:
        return '','unresolved_classification'
    if a == 'unavailable' and b == 'unavailable': return '','excluded_double_unavailable'
    if conflict: return '','review_accession_conflict'
    return '0','complete'


def aggregate(states,records):
    sections=[]
    for s in states:
        rec=records.get(key(s),{})
        result=rec.get('result',{})
        status='unavailable' if not s['text_available'] else result.get('classification') if rec.get('status')=='complete' else rec.get('status','pending')
        sections.append(dict(s,classification=status if status in {'Positive','Negative'} else '',evidence=json.dumps(result.get('evidence',[]),ensure_ascii=False),
                             reason=result.get('reason',rec.get('error','')),classification_status=rec.get('status','unavailable' if not s['text_available'] else 'pending'),
                             evidence_locations=json.dumps(rec.get('quote_locations',[])),prompt_version=rec.get('prompt_version',prompt.PROMPT_VERSION),
                             manual_review_needed=result.get('manual_review_needed',False),review_reason=result.get('review_reason',''),
                             model=MODEL,classified_at_utc=rec.get('classified_at_utc',''),
                             mechanism_summary=result.get('mechanism_summary',''),temporal_basis=result.get('temporal_basis',''),
                             scope_limitation=result.get('scope_limitation','')))
    groups={}
    for s in sections:groups.setdefault(identity(s),{})[s['section']]=s
    panel=[]
    for pair in groups.values():
        a,b=pair['item1a'],pair['item7']
        conflict=bool(a.get('accession_conflict')) and a['text_available'] and b['text_available']
        a_state=a['classification'] if a['classification_status']=='complete' else a['classification_status']
        b_state=b['classification'] if b['classification_status']=='complete' else b['classification_status']
        value,state=decision(a_state,b_state,conflict)
        row={k:a[k] for k in ['cik','ticker','company_name','fiscal_year']}
        row.update(implemented_internal_ai_governance_v2=value,classification_status=state,
                   exclusion_reason='Both sections lack valid observable text' if state=='excluded_double_unavailable' else '',
                   observed_section_count=int(a['text_available'])+int(b['text_available']),
                   source_status='both_observed' if a['text_available'] and b['text_available'] else 'single_section_observed' if a['text_available'] or b['text_available'] else 'double_unavailable',
                   accession_consistent=(a['accession_number']==b['accession_number']) if a['accession_number'] and b['accession_number'] else '',
                   valid_section_accession_conflict=conflict)
        for prefix,s in [('item1a',a),('item7',b)]:
            for target,src in [('text_available','text_available'),('v2_classification','classification'),('evidence','evidence'),('source_reason','source_reason'),('accession','accession_number'),('filing_date','filing_date'),('fiscal_year_end','fiscal_year_end'),('text_path','input_file'),('sha256','input_sha256')]:
                row[prefix+'_'+target]=s[src]
        panel.append(row)
    return sections,panel


def load_records(states):
    saved={}
    def load(s):
        p=cache_file(s)
        return (key(s),json.loads(p.read_text(encoding='utf-8'))) if p.exists() else None
    with ThreadPoolExecutor(max_workers=64) as pool:
        for item in pool.map(load,[s for s in states if s['text_available']]):
            if item is not None:saved[item[0]]=item[1]
    return saved


def report(states,records,meta,final=False):
    sections,panel=aggregate(states,records)
    for sec in ['item1a','item7']:
        rows(OUT/f'{sec}_v2_classification_results.csv',[s for s in sections if s['section']==sec])
    eligible=[r for r in panel if r['source_status']!='double_unavailable']
    excluded=[r for r in panel if r['source_status']=='double_unavailable']
    rows(OUT/'combined_firm_year_v2_panel.csv',eligible)
    rows(OUT/'exclusion_manifest.csv',excluded)
    rows(OUT/'classification_exception_queue.csv',[s for s in sections if s['classification_status'] in {'pending','error','review'}])
    rows(OUT/'source_exception_manifest.csv',[s for s in sections if not s['text_available']])
    rows(OUT/'positive_evidence_audit.csv',[s for s in sections if s['classification']=='Positive'])
    annual=[]
    for y in map(str,range(2020,2026)):
        group=[r for r in panel if r['fiscal_year']==y]
        n=sum(r['source_status']!='double_unavailable' for r in group)
        pos=sum(r['implemented_internal_ai_governance_v2']=='1' for r in group)
        neg=sum(r['implemented_internal_ai_governance_v2']=='0' for r in group)
        unfinished=n-pos-neg
        a=sum(r['item1a_v2_classification']=='Positive' for r in group)
        b=sum(r['item7_v2_classification']=='Positive' for r in group)
        both=sum(r['item1a_v2_classification']==r['item7_v2_classification']=='Positive' for r in group)
        annual.append(dict(fiscal_year=y,target_n=len(group),eligible_n=n,excluded_n=len(group)-n,positive_n=pos,
                           negative_n=neg,unresolved_n=unfinished,positive_rate=pos/n if n and not unfinished else '',
                           statistics_status='complete' if not unfinished else 'incomplete',
                           item1a_available_n=sum(r['item1a_text_available'] for r in group),
                           item7_available_n=sum(r['item7_text_available'] for r in group),
                           item1a_coverage=sum(r['item1a_text_available'] for r in group)/len(group),
                           item7_coverage=sum(r['item7_text_available'] for r in group)/len(group),
                           item1a_positive_n=a,item7_positive_n=b,both_positive_n=both,
                           only_item1a_positive_n=a-both,only_item7_positive_n=b-both))
    rows(OUT/'annual_trend_summary.csv',annual)
    counts=Counter(r['implemented_internal_ai_governance_v2'] for r in eligible)
    usage=Counter(); events=[]
    eventpath=OUT/'request_manifest.jsonl'
    if eventpath.exists():
        with eventpath.open(encoding='utf-8') as f:
            for line in f:
                e=json.loads(line);events.append(e)
                if e['status']=='response_received':usage.update({k:v for k,v in e.get('token_usage',{}).items() if type(v)is int})
    changed=[]
    checks={'unique_firm_year_keys':len({identity(r) for r in panel})==len(panel),
            'unique_section_keys':len({key(r) for r in sections})==len(sections),
            'target_reconciliation':len(panel)==len(eligible)+len(excluded)==meta['target_firm_years'],
            'binary_reconciliation':counts['1']+counts['0']+counts['']==len(eligible),
            'prompt_snapshot_exact':(OUT/'system_prompt.txt').read_text(encoding='utf-8')==system(),
            'no_failed_negative':all(r['classification']!='Negative' for r in sections if r['classification_status'] in {'error','review','pending'}),
            'positive_quotes_located':True, 'request_payloads_exact':True,'no_duplicate_successful_paid_calls':True}
    def check_record(r):
            validate(r['result'],texts(r))
            actual=json.loads((ROOT/r['messages_snapshot']).read_text(encoding='utf-8'))
            digest_valid=sha(json.dumps(actual,ensure_ascii=False).encode())==r['payload_sha256']
            if r.get('recovery_attempted'):
                from .governance_v2_recovery import validate_recovery_snapshot
                return digest_valid and validate_recovery_snapshot(r,actual)
            else:
                expected=request_payload(r)
            return digest_valid and actual==expected
    if final:
        with ThreadPoolExecutor(max_workers=64) as pool:
            checks['request_payloads_exact']=all(pool.map(check_record,[r for r in records.values() if r.get('status') in {'complete','review'}]))
    validated=[e['payload_sha256'] for e in events if e['status']=='validated']
    checks['no_duplicate_successful_paid_calls']=len(validated)==len(set(validated))
    if final:
        protected=json.loads((OUT/'protected_integrity.json').read_text(encoding='utf-8'))
        def changed_file(item):
            p,h=item
            return p if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=h else None
        with ThreadPoolExecutor(max_workers=64) as pool:
            changed=[p for p in pool.map(changed_file,protected.items()) if p]
        checks['protected_inputs_and_old_outputs_unchanged']=not changed
    qa=dict(passed=all(checks.values()),checks=checks,changed_protected_files=changed,
            all_eligible_binary_complete=counts['']==0,source_exception_counts=dict(Counter(s['source_reason'] for s in sections if not s['text_available'])))
    dump(OUT/'qa.json',qa)
    meta.update(status='complete' if final and not counts[''] else 'incomplete' if final else 'running',
                updated_at_utc=now(),eligible_n=len(eligible),excluded_n=len(excluded),positive_n=counts['1'],negative_n=counts['0'],
                unresolved_n=counts[''],api_attempts=sum(e['status']=='started' for e in events),
                received_responses=sum(e['status']=='response_received' for e in events),token_usage=dict(usage),cost=None,
                classified_sections=sum(s['classification'] in {'Positive','Negative'} for s in sections),
                review_sections=sum(s['classification']=='review' for s in sections),qa_passed=qa['passed'])
    dump(OUT/'run_manifest.json',meta)
    dump(OUT/'cost_and_token_summary.json',dict(api_attempts=meta['api_attempts'],usage=dict(usage),cost=None,reason='No verified price snapshot; no invented cost'))
    cost_estimates=None
    pricepath=OUT/'pricing_snapshot.json'
    if pricepath.exists():
        price=json.loads(pricepath.read_text(encoding='utf-8'))
        needed=('prompt_cache_hit_tokens','prompt_cache_miss_tokens','completion_tokens')
        received=[e for e in events if e['status']=='response_received']
        missing=sum(any(type(e.get('token_usage',{}).get(k)) is not int for k in needed) for e in received)
        if not missing:
            cost_estimates={currency:{period:sum(usage[k]*rates[k]/1e6 for k in needed) for period,rates in price[currency].items()} for currency in ['USD','CNY']}
        dump(OUT/'cost_and_token_summary.json',dict(api_attempts=meta['api_attempts'],responses_received=len(received),
            usage=dict(usage),actual_account_cost=None,list_price_estimates=cost_estimates,
            response_usage_incomplete_n=missing,unreceived_attempts=meta['api_attempts']-len(received),
            pricing_snapshot=rel(pricepath),estimate_note=price['estimate_note']))
    if final: figures(annual)
    rate=f"{counts['1']/len(eligible):.4%}" if eligible and not counts[''] else 'Not final: unresolved classifications remain'
    lines=['# Full-Universe Implemented Internal AI Governance v2','', '## A. Executive Summary','',
           f"Status: {meta['status']}. Target={len(panel)}; Eligible={len(eligible)}; Excluded={len(excluded)}; Positive={counts['1']}; Negative={counts['0']}; Unresolved={counts['']}. Overall Positive Rate: {rate}.",
           'Model estimates of disclosed evidence; no human-review decisions or governance quality scores are inferred.',
           '', '## B. Data Coverage','',
           f"Item 1A valid text: {sum(s['text_available'] for s in sections if s['section']=='item1a')}/{len(panel)}. Item 7 valid text: {sum(s['text_available'] for s in sections if s['section']=='item7')}/{len(panel)}.",
           'Source exceptions: `source_exception_manifest.csv`; double-unavailable observations: `exclusion_manifest.csv`; unresolved LLM cases: `classification_exception_queue.csv`. Reasons distinguish acquisition, extraction, identity, incorporated-reference and input-validation failures.',
           'Item 1A uses original automatic-pass text, independently verified original text, and saved secondary repaired_verified text with matching accession/hash. The latest review-repair comparison overrides older verification; unresolved staged candidates and filing-selection cases remain unavailable. Item 7 uses the latest v2.4 extraction manifest, success plus automatic_pass only.',
           '', '## C. LLM Configuration','',
           f"DeepSeek / `{MODEL}` (intended `{INTENDED_MODEL_VERSION}`); temperature=0; max_tokens={MAX_TOKENS}; JSON object response; timeout=120s; 3 transport retries, 2/4/8s backoff; at most {VALIDATION_REQUEST_LIMIT} validation requests. Concurrency={meta.get('workers','not run')}.",
           f"Settings baseline: `{rel(BASELINE)}`, the most recent completed full-universe Item 7 governance workflow (2026-10-10). Same shared DeepSeek client and payload builder; only an optional raw-response capture callback was added.",
           f"Prompt `{prompt.PROMPT_VERSION}`: `system_prompt.txt`, `user_prompt_template.txt`; complete authoritative standard: `classification_standard_snapshot.md`. API attempts={meta['api_attempts']}; received responses={meta['received_responses']}. Tokens={dict(usage)}. Monetary cost unavailable without verified pricing; credentials excluded.",
           'Every attempt is in `request_manifest.jsonl`, referring to exact full message snapshots in `requests/`; raw API responses are in `responses/`, validated results and source quote offsets in `cache/`. Hashes link source bytes, prompts, request payload and response. Resumes use the same source/prompt/configuration digest and skip all completed or review responses.',
           '', '## D. Classification Results','',
           '| FY | Target | Eligible | Excluded | Positive | Negative | Unresolved | Positive Rate | 1A Positive | 7 Positive | Both | Only 1A | Only 7 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in annual:
        rate_y=f"{r['positive_rate']:.3%}" if r['positive_rate']!='' else 'Incomplete'
        lines.append(f"| {r['fiscal_year']} | {r['target_n']} | {r['eligible_n']} | {r['excluded_n']} | {r['positive_n']} | {r['negative_n']} | {r['unresolved_n']} | {rate_y} | {r['item1a_positive_n']} | {r['item7_positive_n']} | {r['both_positive_n']} | {r['only_item1a_positive_n']} | {r['only_item7_positive_n']} |")
    lines += ['', '## E. Figures','', '![Annual positive rate](figures/figure1_annual_positive_rate.png)',
              '![Annual positive count](figures/figure2_annual_positive_count.png)',
              '![Combined figures](figures/combined_annual_trends.png)',
              'Figures use annual Eligible N. Unfinished years have no final rate; provisional identified-positive counts are explicitly labeled. PNG 300 dpi and vector PDF.',
              '', '## F. QA and Limitations','',f"QA checks passed: {qa['passed']}; all eligible binary complete: {qa['all_eligible_binary_complete']}. Details: `qa.json`.",
              'The user task section 5.1 explicitly adopts an observed-section estimator: a single available classified Negative plus unavailable text is 0. This is the expressly selected alternative permitted by standard section 5.2; it does not establish a complete two-section negative. `source_status` and coverage flags retain that distinction.',
              'OR returns 1 for qualifying evidence in either section; unresolved classification in the other section is retained in its exception queue. With no positive, pending/review/API/JSON errors block 0. Dual unavailable valid text alone causes exclusion. Conflicting accessions among valid chapters are held for review.',
              'Automated extraction checks cannot establish human boundary correctness. Missing/unverified text can select the eligible sample; current frozen index constituents also create survivorship/selection limits. Negative denotes absent evidence in observed disclosure, not absent real governance.',
              'v2 requires C1-C5 and excludes bare restrictions unless additional implemented institutional evidence exists. v1 labels and G/R subtype fields were neither input nor mapped into v2. A positive quote source match establishes traceability, not semantic correctness; `positive_evidence_audit.csv` retains all positive cases for inspection.',
              'Model material timing/actor/mechanism ambiguity remains an explicit null review state. Annual rates are withheld for unfinished years. No causal or governance-quality inference is made.',
              '', '## Artifact paths','']
    if cost_estimates is not None:
        costline=f"Published list-price scenarios based on all API-returned usage (including received retries): USD {cost_estimates['USD']['off_peak']:.4f} off-peak / {cost_estimates['USD']['peak']:.4f} peak; CNY {cost_estimates['CNY']['off_peak']:.4f} / {cost_estimates['CNY']['peak']:.4f}. Account invoice, currency and credit deductions were not retrieved. Sources: [DeepSeek USD pricing](https://api-docs.deepseek.com/quick_start/pricing/) and [CNY pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/), snapshot retrieved 2026-10-13. See `pricing_snapshot.json` and `cost_and_token_summary.json`."
        index=lines.index('## D. Classification Results')
        lines[index:index]=[costline,'']
        # Replace the historical unavailable-price sentence with current, bounded estimates.
        lines=[l.replace('Monetary cost unavailable without verified pricing; credentials excluded.','Actual account cost unavailable; verified list-price scenarios are reported below; credentials excluded.') for l in lines]
    coverage=['| FY | Item 1A N | Item 1A Coverage | Item 7 N | Item 7 Coverage | Double Unavailable |',
              '|---|---:|---:|---:|---:|---:|']
    coverage += [f"| {r['fiscal_year']} | {r['item1a_available_n']} | {r['item1a_coverage']:.2%} | {r['item7_available_n']} | {r['item7_coverage']:.2%} | {r['excluded_n']} |" for r in annual]
    index=lines.index('## C. LLM Configuration')
    lines[index:index]=coverage+['']
    if (OUT/'offline_response_recovery.csv').exists() or (OUT/'corrective_recovery_summary.csv').exists():
        offline=read(OUT/'offline_response_recovery.csv') if (OUT/'offline_response_recovery.csv').exists() else []
        corrected=read(OUT/'corrective_recovery_summary.csv') if (OUT/'corrective_recovery_summary.csv').exists() else []
        index=lines.index('## F. QA and Limitations')+2
        lines[index:index]=[f"Response recovery: {len(offline)} offline recoveries preserved the original binary label and used only ignored extra JSON metadata or unique typography/whitespace matches converted back to exact source spans. {len(corrected)} unresolved sections received one corrective full-text request with the identical system standard and model settings. Corrections are separately versioned, have a saved user suffix template and complete request snapshots; original failed caches and raw responses remain retained. `offline_response_recovery.csv`, `corrective_recovery_summary.csv`, `recovery_originals/`, `recovery_llm_config.json` document this process.",'']
    lines += [f'- `{rel(OUT/p)}`' for p in ['item1a_v2_classification_results.csv','item7_v2_classification_results.csv','combined_firm_year_v2_panel.csv','annual_trend_summary.csv','exclusion_manifest.csv','positive_evidence_audit.csv','classification_exception_queue.csv','qa.json','request_manifest.jsonl','llm_config.json','run_manifest.json']]
    (OUT/'run_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return qa


def figures(annual):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    dest=OUT/'figures';dest.mkdir(exist_ok=True)
    complete=all(r['positive_rate']!='' for r in annual)
    def draw(ax,kind):
        x=[int(r['fiscal_year']) for r in annual]
        if kind=='rate':
            y=[100*r['positive_rate'] if r['positive_rate']!='' else float('nan') for r in annual]
            ax.plot(x,y,color='#21618C',marker='o',lw=2)
            ax.set(title='Annual Positive Rate',ylabel='Implemented Internal AI Governance v2 (%)')
            for a,b in zip(x,y):
                if b==b:ax.annotate(f'{b:.2f}%',(a,b),xytext=(0,7),textcoords='offset points',ha='center')
            ymax=max([v for v in y if v==v]+[1]);ax.set_ylim(0,ymax*1.3)
        else:
            y=[r['positive_n'] for r in annual]
            ax.bar(x,y,color='#21618C',width=.62)
            ax.set(title='Annual Positive Count'+('' if complete else ' (Provisional)'),ylabel='Positive Firm-Year Count')
            for a,b in zip(x,y):ax.annotate(str(b),(a,b),xytext=(0,5),textcoords='offset points',ha='center')
            ax.set_ylim(0,max(y+[1])*1.3)
        ax.set_xticks(x);ax.set_xlabel('Fiscal Year');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    note='Positive Rate = Positive N / Eligible N; Eligible: at least one valid section. Observed-section OR estimate.'
    if not complete:note+=' Incomplete years: final rate withheld.'
    for name,kind in [('figure1_annual_positive_rate','rate'),('figure2_annual_positive_count','count')]:
        fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained');draw(ax,kind)
        fig.text(.5,-.03,note,ha='center',fontsize=8,wrap=True)
        for suffix in ['png','pdf']:fig.savefig(dest/f'{name}.{suffix}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
    draw(axs[0],'rate');draw(axs[1],'count');fig.suptitle('Implemented Internal AI Governance v2: FY2020–FY2025')
    fig.text(.5,-.03,note,ha='center',fontsize=8)
    for suffix in ['png','pdf']:fig.savefig(dest/f'combined_annual_trends.{suffix}',dpi=300,bbox_inches='tight')
    plt.close(fig)


def pilot_sample(states):
    available=[s for s in states if s['text_available']]
    chosen=[]
    # Four actual source disclosures spanning both sections and v2 mechanism boundary.
    for section in ['item1a','item7']:
        rs=[s for s in available if s['section']==section]
        negatives=[s for s in rs if s['fiscal_year']=='2020']
        chosen.append(sorted(negatives,key=lambda s:s['text_characters'])[len(negatives)//2])
        # Actual source-inspected policy/framework cases, selected independently
        # of any v1 label, exercise the Positive evidence locator.
        inspected_ticker='TREX' if section=='item1a' else 'ALGN'
        matches=[s for s in rs if s['fiscal_year']=='2025' and s['ticker']==inspected_ticker]
        if not matches: raise ValueError('Source-inspected pilot record is not eligible')
        chosen.append(matches[0])
    rows(OUT/'pilot_sample.csv',chosen)
    return chosen


def run(stage='full',workers=32):
    if workers<1 or workers>64:raise ValueError('Workers must be 1..64')
    states,meta=prepare()
    if stage=='prepare':return
    # Compute request identities once per source snapshot; avoid repeated full-text
    # I/O during checkpoint lookup and periodic aggregate refreshes.
    tohash=[s for s in states if s['text_available'] and 'request_payload_sha256' not in s]
    def identify_request(s):
        s['request_payload_sha256']=sha(json.dumps(request_payload(s),ensure_ascii=False).encode())
        return s
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i,f in enumerate(as_completed([pool.submit(identify_request,s) for s in tohash]),1):
            f.result()
            if i%4000==0 or i==len(tohash):log(f'Request identities: {i}/{len(tohash)}')
    if stage != 'prepare':
        dump(OUT/'input_manifest.json',states)
    records=load_records(states)
    if stage=='report':
        report(states,records,meta,True);return
    config=load_config(prior._env_file());lock=threading.Lock()
    samples=pilot_sample(states)
    pilot=[]
    for s in samples:
        r=execute(s,config,lock);records[key(s)]=r;pilot.append(r)
        log(f"Pilot: {s['ticker']} FY{s['fiscal_year']} {s['section']} {r['status']} {r.get('result',{}).get('classification')}")
    passed=all(r['status']=='complete' for r in pilot)
    dump(OUT/'pilot_gate.json',dict(passed=passed,checked_at_utc=now(),sample_keys=[key(s) for s in samples],
                                 source_quote_validation=True,results=[r.get('result',r.get('error')) for r in pilot]))
    report(states,records,meta)
    if not passed:raise RuntimeError('Pilot has unresolved failures; inspect pilot_gate.json before full run')
    if stage=='pilot':return
    todo=[s for s in states if s['text_available'] and records.get(key(s),{}).get('status') not in {'complete','review'}]
    meta['workers']=workers
    meta['code_hashes_at_execution']={rel(p):sha(p.read_bytes()) for p in [Path(__file__),ROOT/'src/ai_restrictions/llm/governance_v2_prompt.py',ROOT/'src/ai_restrictions/llm/client.py']}
    for p in [Path(__file__),ROOT/'src/ai_restrictions/llm/governance_v2_prompt.py',ROOT/'src/ai_restrictions/llm/client.py']:
        dest=OUT/'code_snapshot'/p.name
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(p.read_bytes())
    billing_stop=threading.Event()
    def safe_execute(s):
        if billing_stop.is_set():
            return dict(s,status='pending',error='Not submitted: provider HTTP 402 circuit breaker',validation_requests=0)
        try:
            r=execute(s,config,lock)
            if r.get('error')=='RuntimeError: DeepSeek HTTP 402':
                billing_stop.set()
            return r
        except Exception as exc:
            return dict(s,status='error',error=f'{type(exc).__name__}: {exc}',validation_requests=0)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(safe_execute,s) for s in todo]
        for i,f in enumerate(as_completed(futures),1):
            r=f.result();records[key(r)]=r
            if i%100==0 or i==len(todo):
                log(f"Full: {i}/{len(todo)}; errors={sum(r.get('status')=='error' for r in records.values())}; reviews={sum(r.get('status')=='review' for r in records.values())}")
            if i%2000==0:report(states,records,meta)
    if billing_stop.is_set():
        meta['provider_blocker']='DeepSeek HTTP 402; queued requests were not submitted after circuit breaker'
    qa=report(states,records,meta,True)
    log(json.dumps(dict(output_directory=str(OUT),qa_passed=qa['passed'],summary={k:meta[k] for k in ['status','eligible_n','excluded_n','positive_n','negative_n','unresolved_n','api_attempts','token_usage']}),ensure_ascii=False))
    if not qa['passed']:raise RuntimeError('Final QA failed')
