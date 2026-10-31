"""Full-text Item 7 adapter for the shared governance classifier.

Model results remain provisional in interim; existing Item 1A and Item 7 inputs
are read-only. This module does no acquisition, extraction or human review.
"""
from __future__ import annotations
import json
import random
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import implemented_governance as gov
from . import item1a_semantic as prior
from .llm import item7_governance_prompt as prompt
from .llm.client import MODEL, INTENDED_MODEL_VERSION, load_config

ROOT = prior.ROOT
MANIFEST = ROOT / 'data/interim/documents/full_universe_item7/optimization_v2/manifest_item7-secondary-v2.4.csv'
OUT = ROOT / 'data/interim/classifications/full_universe_item7_implemented_internal_ai_governance/v1'
ITEM1A = ROOT / 'outputs/full_universe_implemented_internal_ai_governance'
STANDARD = ROOT / 'docs/implemented_internal_ai_governance.md'
TYPES = ('G1', 'G2', 'G3', 'R1', 'R2')
MAX_TOKENS = 16384


def identity(row):
    # The fixed universe retains six blank-CIK MOG.A observations. These remain
    # unclassified; join their identical frozen issuer key without inventing CIK.
    issuer = 'CIK:'+str(int(row['cik'])) if row['cik'] else 'FROZEN_TICKER:'+row['ticker']
    return issuer, str(row['fiscal_year'])


def relative(path):
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        prior._write_csv(path, rows, list(rows[0]))


def system_prompt():
    return prompt.SYSTEM_PROMPT.format(criteria=STANDARD.read_text(encoding='utf-8-sig'))


def candidate(row):
    data = (ROOT / row['item7_path']).read_bytes()
    if gov.sha(data) != row['item7_sha256']:
        raise ValueError('Item 7 source hash changed')
    text = data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    if not text.strip():
        raise ValueError('Empty Item 7 text')
    c = {'company_name': row['company_name'], 'ticker': row['ticker'],
         'fiscal_year': row['fiscal_year'], 'candidate_id': f"{row['ticker']}-ITEM7-FULL",
         'candidate_text': text, 'surrounding_context': '',
         'subsection_heading': 'Item 7. Management Discussion and Analysis'}
    payload = json.dumps({'company': c['company_name'], 'ticker': c['ticker'],
                          'fiscal_year': c['fiscal_year'], 'section': 'Item 7 (MD&A)',
                          'item7_full_text': text}, ensure_ascii=False)
    # A conservative UTF-8 byte upper bound, including escaped JSON and framing.
    bound = len(payload.encode()) + len(system_prompt().encode()) + MAX_TOKENS + 2048
    if bound >= 1_000_000:
        raise ValueError('Conservative input bound exceeds documented 1M context')
    return c, payload, bound


def freeze_pilot(rows):
    selected = []
    for year in map(str, range(2020, 2026)):
        group = sorted([r for r in rows if r['fiscal_year'] == year],
                       key=lambda r: (int(r['item7_characters']), identity(r)))
        chosen = [group[0], group[len(group)//2], group[int(len(group)*.85)], group[-1]]
        other_source = [r for r in group if r['source_type'] == 'sec_html' and r not in chosen]
        if other_source:
            chosen.append(other_source[len(other_source)//2])
        else:
            # Additional rule-boundary example; selection uses Item 7 alone.
            likely = [r for r in group if r not in chosen and re.search(
                r'(?i)(responsible AI|AI governance|AI polic|artificial intelligence.{0,100}(control|govern|polic))',
                (ROOT/r['item7_path']).read_text(encoding='utf-8-sig'))]
            chosen.append(likely[0] if likely else group[len(group)//4])
        assert len({identity(r) for r in chosen}) == 5
        selected.extend(chosen)
    return [dict(r, pilot_length_stratum=str(i % 5), pilot_selection_seed='20261010') for i, r in enumerate(selected)]


def protected_files(rows):
    paths = {MANIFEST, ROOT/'data/interim/documents/full_universe_item7_manifest.csv',
             ROOT/'data/interim/documents/full_universe_item1a_manifest.csv', STANDARD}
    paths.update(p for p in ITEM1A.rglob('*') if p.is_file())
    review = ROOT/'data/interim/human_review'
    if review.exists():
        paths.update(p for p in review.rglob('*') if p.is_file())
    paths.update(ROOT/r['item7_path'] for r in rows if r['item7_path'])
    paths.update(p for p in (ROOT/'data/interim/documents/full_universe_item7_text').rglob('*.txt'))
    paths.update(ROOT/r['item1a_text_path'] for r in prior.read_csv(ITEM1A/'firm_year_panel.csv') if r['item1a_text_path'])
    return [{'path': relative(p), 'sha256': gov.sha(p.read_bytes())} for p in sorted(paths) if p.exists()]


def prepare(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out/'run_manifest.json'
    rows = prior.read_csv(MANIFEST)
    assert len(rows) == len({identity(r) for r in rows})
    assert len(rows) == len({(r['ticker'],r['fiscal_year']) for r in rows})
    successes = [r for r in rows if r['extraction_status'] == 'success']
    meta = {'run_version': 'item7-implemented-governance-v1', 'started_at_utc': prior._now(),
            'input_manifest': relative(MANIFEST), 'input_manifest_sha256': gov.sha(MANIFEST.read_bytes()),
            'criteria_sha256': gov.sha(STANDARD.read_bytes()), 'system_prompt_sha256': gov.sha(system_prompt().encode()),
            'prompt_version': prompt.PROMPT_VERSION, 'model': MODEL, 'intended_model_version': INTENDED_MODEL_VERSION,
            'context_limit': 1_000_000, 'max_output_tokens': MAX_TOKENS,
            'context_reference': 'https://api-docs.deepseek.com/quick_start/pricing/',
            'full_text_input': True, 'keyword_screening': False, 'item1a_labels_in_input': False,
            'universe_n': len(rows), 'target_n': len(successes),
            'extraction_counts': dict(Counter(r['extraction_status'] for r in rows)),
            'status': 'prepared'}
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding='utf-8'))
        for key in ('input_manifest_sha256','criteria_sha256','system_prompt_sha256','model','prompt_version'):
            if old[key] != meta[key]:
                raise ValueError('Resume identity changed: '+key)
        old['max_output_tokens']=MAX_TOKENS
        old['code_hashes_current']={relative(p):gov.sha(p.read_bytes()) for p in
                                  (Path(__file__), ROOT/'src/ai_restrictions/implemented_governance.py',
                                   ROOT/'src/ai_restrictions/llm/client.py',ROOT/'src/ai_restrictions/llm/item7_governance_prompt.py')}
        old['max_conservative_token_bound']=old['max_conservative_token_bound'] + max(0, MAX_TOKENS-old.get('coverage_output_reservation',4096))
        old['coverage_output_reservation']=MAX_TOKENS
        prior._write_json(meta_path,old)
        return rows, old
    checks = []
    for row in successes:
        c, payload, bound = candidate(row)
        checks.append({'cik':row['cik'], 'ticker':row['ticker'], 'fiscal_year':row['fiscal_year'],
                       'item7_path':row['item7_path'], 'item7_sha256':row['item7_sha256'],
                       'text_characters':len(c['candidate_text']), 'conservative_token_bound':bound,
                       'payload_sha256':gov.sha(payload.encode()), 'coverage_start':0,
                       'coverage_end':len(c['candidate_text']), 'full_text_covered':True})
    write_rows(out/'input_manifest.csv', rows)
    write_rows(out/'full_text_coverage.csv', checks)
    write_rows(out/'pilot_sample.csv', freeze_pilot(successes))
    write_rows(out/'protected_integrity_before.csv', protected_files(rows))
    (out/'system_prompt.txt').write_text(system_prompt(), encoding='utf-8')
    meta['max_conservative_token_bound'] = max(r['conservative_token_bound'] for r in checks)
    meta['code_hashes'] = {relative(p):gov.sha(p.read_bytes()) for p in
                           (Path(__file__), ROOT/'src/ai_restrictions/implemented_governance.py',
                            ROOT/'src/ai_restrictions/llm/client.py', ROOT/'src/ai_restrictions/llm/item7_governance_prompt.py')}
    prior._write_json(meta_path, meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)
    return rows, meta


def quote_location(text, quote):
    if not quote:
        return None
    direct = text.find(quote)
    if direct >= 0:
        return {'start':direct, 'end':direct+len(quote), 'method':'exact'}
    # Shared validation permits whitespace normalization; map it back to offsets.
    pattern = r'\s+'.join(re.escape(w) for w in quote.split())
    match = re.search(pattern, text, re.I)
    return {'start':match.start(), 'end':match.end(), 'method':'normalized_whitespace_case'} if match else None


def execute(row, config, out, observer):
    base = {k:row[k] for k in ('cik','ticker','fiscal_year','accession_number','source_type','item7_path','item7_sha256')}
    base.update(prompt_version=prompt.PROMPT_VERSION, model=MODEL, classified_at_utc=prior._now())
    try:
        c, payload, bound = candidate(row)
        record = gov.classify(c, system_prompt(), config, out, observer,
                              prompt_version=prompt.PROMPT_VERSION, payload=payload,max_tokens=MAX_TOKENS)
        if record.get('returned_model','').lower() not in {MODEL.lower(), INTENDED_MODEL_VERSION.lower()}:
            raise ValueError('Unexpected returned model')
        locations = {field:quote_location(c['candidate_text'],record['result'][field])
                     for field in ('implementation_evidence','ai_specificity_evidence')}
        if any(record['result'][field] and loc is None for field,loc in locations.items()):
            raise ValueError('Quote cannot be located in full Item 7')
        base.update(result=record['result'], metadata={k:v for k,v in record.items() if k != 'result'},
                    quote_locations=locations, full_text_covered=True, text_characters=len(c['candidate_text']),
                    conservative_token_bound=bound, payload_sha256=gov.sha(payload.encode()),
                    cache_path=relative(gov.cache_path(c,system_prompt(),out,prompt_version=prompt.PROMPT_VERSION,payload=payload)))
    except Exception as exc:
        base.update(error=f'{type(exc).__name__}: {exc}', full_text_covered=False)
    return base


def aggregate(rows, records):
    by = {identity(r):r for r in records}
    panel=[]
    for r in rows:
        rec=by.get(identity(r), {})
        result=rec.get('result', {})
        excluded=r['extraction_status'] != 'success'
        state = 'not_eligible_'+r['extraction_status'] if excluded else 'technical_failure' if 'error' in rec else result.get('classification','pending')
        value = result.get('implemented_internal_ai_governance') if result and not excluded else None
        row = {k:r[k] for k in ('company_name','ticker','cik','fiscal_year','accession_number','source_type','source_path','source_sha256','item7_path','item7_sha256','qa_rule_version','source_cik','identity_resolution_basis')}
        row.update(extraction_status=r['extraction_status'],classification_status=state,
                   implemented_internal_ai_governance='' if value is None else str(value),
                   classification_valid=int(state in {'positive','negative'} and rec.get('full_text_covered',False)),
                   classifier_execution_valid=int(bool(result)),full_text_covered=int(rec.get('full_text_covered',False)),
                   governance_evidence_type=json.dumps(result.get('governance_evidence_type',[])),
                   implementation_evidence=result.get('implementation_evidence',''),
                   ai_specificity_evidence=result.get('ai_specificity_evidence',''),reason=result.get('reason',''),
                   manual_review=result.get('manual_review',False),review_reason=result.get('review_reason',rec.get('error','')),
                   prompt_version=prompt.PROMPT_VERSION if rec else '',model=MODEL if rec else '',
                   evidence_locations=json.dumps(rec.get('quote_locations',{})))
        for t in TYPES:
            row[t]=int(t in result.get('governance_evidence_type',[])) if value is not None else ''
        panel.append(row)
    return panel


def run(stage='pilot', workers=16, out=OUT):
    rows,meta=prepare(out)
    if stage == 'prepare':
        return
    if stage == 'full':
        gate=json.loads((out/'pilot_gate.json').read_text(encoding='utf-8'))
        if not gate.get('passed'):
            raise RuntimeError('Pilot independent source inspection gate has not passed')
    selected=prior.read_csv(out/'pilot_sample.csv') if stage == 'pilot' else [r for r in rows if r['extraction_status']=='success']
    if stage == 'pilot' and (out/'pilot_supplement.csv').exists():
        selected += prior.read_csv(out/'pilot_supplement.csv')
    config=load_config(prior._env_file())
    lock=threading.Lock()
    saved={identity(r):r for r in jsonl(out/'classification_results.jsonl')}
    # Validated successes are never repurchased. Raw validation failures also
    # remain cached and are revalidated without a second paid call on resume.
    todo=[r for r in selected if 'result' not in saved.get(identity(r),{})]
    with (out/'api_attempts.jsonl').open('a',encoding='utf-8') as attempts, (out/'classification_results.jsonl').open('a',encoding='utf-8') as results:
        def observe(row):
            def emit(event):
                data={**{k:row[k] for k in ('cik','ticker','fiscal_year')},'timestamp_utc':prior._now(), 'stage':stage,**event}
                with lock:
                    attempts.write(json.dumps(data,ensure_ascii=False)+'\n'); attempts.flush()
            return emit
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(execute,r,config,out,observe(r)) for r in todo]
            for n,f in enumerate(as_completed(futures),1):
                rec=f.result(); saved[identity(rec)]=rec
                results.write(json.dumps(rec,ensure_ascii=False)+'\n'); results.flush()
                if n % 25 == 0 or n == len(todo):
                    print(f"{stage}: {n}/{len(todo)} new tasks; stored={len(saved)}; failed={sum('error' in r for r in saved.values())}",flush=True)
                if n % 100 == 0:
                    write_rows(out/'firm_year_panel.csv',aggregate(rows,list(saved.values())))
    records=sorted(saved.values(),key=identity)
    panel=aggregate(rows,records)
    write_rows(out/'firm_year_panel.csv',panel)
    write_rows(out/'manual_review_queue.csv',[r for r in panel if r['manual_review'] or r['classification_status']=='technical_failure'])
    usage=Counter()
    events=jsonl(out/'api_attempts.jsonl')
    for e in events:
        if e['status']=='response_received':
            usage.update({k:v for k,v in e.get('token_usage',{}).items() if type(v) is int})
    meta.update(status=stage+'_complete',updated_at_utc=prior._now(),workers=workers,
                classified_n=sum(bool(r.get('result')) for r in records),
                binary_valid_n=sum(r['classification_valid'] for r in panel),
                classification_counts=dict(Counter(r['classification_status'] for r in panel)),
                token_usage_all_received_attempts=dict(usage), api_attempts=sum(e['status']=='started' for e in events),
                responses_received=sum(e['status']=='response_received' for e in events),
                successful_response_cache_n=sum(1 for p in (out/'cache').glob('*.json')))
    prior._write_json(out/'run_manifest.json',meta)
    print(json.dumps(meta,ensure_ascii=False),flush=True)


def derived(a,b):
    """Three-state OR and incremental indicator, without imputing unknowns."""
    either='1' if a=='1' or b=='1' else '0' if a=='0' and b=='0' else ''
    incremental=('1' if a=='0' and b=='1' else '0') if a in {'0','1'} and b in {'0','1'} else ''
    return either,incremental


def merge_panel(panel):
    base=prior.read_csv(ITEM1A/'firm_year_panel.csv')
    by={identity(r):r for r in panel}
    if len(by)!=len(panel) or len({identity(r) for r in base})!=len(base):
        raise ValueError('Duplicate panel key')
    merged=[]; mismatches=[]
    for a in base:
        b=by.get(identity(a))
        if b is None:
            raise ValueError('Missing Item 7 universe identity')
        if not a['cik'] and a['company'] != b['company_name']:
            raise ValueError('Blank-CIK frozen issuer name mismatch')
        same_acc=a['accession_number']==b['accession_number']
        if a['accession_number'] and b['accession_number'] and not same_acc:
            mismatches.append({'cik':a['cik'],'ticker':a['ticker'],'fiscal_year':a['fiscal_year'],
                               'item1a_accession':a['accession_number'],'item7_accession':b['accession_number'],
                               'basis':'same fixed CIK/FY; accession differs; Item7 extraction status='+b['extraction_status']+'; retain separate provenance and unresolved state'})
        r=dict(a)
        for k,v in b.items():
            r['item7_'+k]=v
        r['item7_accession_matches_item1a']=int(same_acc)
        r['item7_ticker_matches_item1a']=int(a['ticker']==b['ticker'])
        r['item7_cross_chapter_identity_valid']=int(bool(a['cik'] and a['accession_number'] and b['accession_number'] and same_acc))
        r['item7_join_basis']='CIK+FY' if a['cik'] else 'identical fixed-universe ticker+company+FY; blank CIK retained'
        r['iag_either_item1a_item7'],r['iag_item7_incremental']=derived(a['implemented_internal_ai_governance'],b['implemented_internal_ai_governance'])
        r['iag_item7_incremental_applicable']=int(a['implemented_internal_ai_governance']=='0' and b['implemented_internal_ai_governance'] in {'0','1'} and r['item7_cross_chapter_identity_valid']==1)
        if not r['item7_cross_chapter_identity_valid']:
            r['iag_item7_incremental']=''
        merged.append(r)
    assert len(merged)==len(base)
    assert all(all(r[k]==a[k] for k in a) for a,r in zip(base,merged))
    return merged,mismatches


def verify(out=OUT):
    rows,meta=prepare(out)
    records=list({identity(r):r for r in jsonl(out/'classification_results.jsonl')}.values())
    panel=aggregate(rows,records)
    protected=prior.read_csv(out/'protected_integrity_before.csv')
    changed=[r['path'] for r in protected if not (ROOT/r['path']).exists() or gov.sha((ROOT/r['path']).read_bytes())!=r['sha256']]
    expected_keys={identity(r) for r in rows if r['extraction_status']=='success'}
    actual_keys={identity(r) for r in records}
    checks={'universe_n':len(rows),'success_n':sum(r['extraction_status']=='success' for r in rows),
            'attempted_unique_n':len(records),'unique_panel_keys':len({identity(r) for r in panel}),
            'all_success_attempted':actual_keys==expected_keys,
            'missing_target_keys':sorted(expected_keys-actual_keys),'unexpected_record_keys':sorted(actual_keys-expected_keys),
            'protected_files_n':len(protected),'protected_files_changed':changed,
            'failed_coded_negative':sum(r['classification_status']=='technical_failure' and r['implemented_internal_ai_governance']=='0' for r in panel),
            'excluded_coded_negative':sum(r['extraction_status']!='success' and r['implemented_internal_ai_governance']=='0' for r in panel),
            'valid_without_full_coverage':sum(r['classification_valid'] and not r['full_text_covered'] for r in panel)}
    locator_errors=[]
    source_by={identity(r):r for r in rows}
    for rec in records:
        if not rec.get('result'):
            continue
        source=source_by[identity(rec)]
        c,payload,bound=candidate(source)
        gov.validate(rec['result'],c)
        if gov.sha(payload.encode())!=rec['payload_sha256']:
            raise ValueError('Saved response payload identity mismatch')
        for field,location in rec['quote_locations'].items():
            quote=rec['result'][field]
            if quote and (not location or gov.norm(c['candidate_text'][location['start']:location['end']])!=gov.norm(quote)):
                locator_errors.append([rec['ticker'],rec['fiscal_year'],field])
    merged,mismatches=merge_panel(panel)
    checks.update(quote_locator_errors=locator_errors,merged_n=len(merged),accession_mismatch_n=len(mismatches),
                  classified_accession_mismatch_n=sum(r['item7_classification_valid']==1 and r['implemented_internal_ai_governance'] in {'0','1'} and not r['item7_cross_chapter_identity_valid'] for r in merged),
                  original_item1a_fields_preserved=True)
    checks['passed']=checks['all_success_attempted'] and not (changed or locator_errors or checks['failed_coded_negative'] or checks['excluded_coded_negative'] or checks['valid_without_full_coverage'])
    prior._write_json(out/'qa.json',checks)
    write_rows(out/'accession_match_audit.csv',mismatches)
    print(json.dumps(checks,ensure_ascii=False),flush=True)
    return panel,merged,checks
