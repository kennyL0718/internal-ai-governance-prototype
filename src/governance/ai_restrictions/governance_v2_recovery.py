"""Offline v2 response recovery with explicit, content-preserving audit trail.

Only extra JSON keys and typography/whitespace can be repaired here. No changed
governance label, missing evidence, semantic paraphrase or source inference is allowed.
"""
from __future__ import annotations
import json
import re
import unicodedata
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from . import governance_v2 as v
from .llm.client import chat_json,load_config,build_payload

PUNCT = str.maketrans({'‘':"'",'’':"'",'“':'"','”':'"','–':'-','—':'-','−':'-',
                       '\u00ad':'','\u200b':'','\ufeff':''})


PAGINATION=re.compile(r'(?im)(?:^|\n)[ \t]*\d{1,4}[ \t]*(?:\r?\n[ \t]*){1,4}Table[ \t]+of[ \t]+Contents[ \t]*(?:\r?\n|$)')


def canonical(text,pagination=False,verified_page_spans=()):
    chars=[]; mapping=[]
    noise=set()
    if pagination:
        for m in PAGINATION.finditer(text):noise.update(range(m.start(),m.end()))
    for start,end in verified_page_spans:
        if not re.fullmatch(r'\n(?:[ \t]*\n)*[ \t]*\d{1,4}[ \t]*\n(?:[ \t]*\n)*',text[start:end]):
            raise ValueError('Verified override must be an isolated numeric page line')
        noise.update(range(start,end))
    for i,c in enumerate(text):
        if i in noise:
            # Retain a separator and original offsets; only the recognized paired
            # standalone page-number/TOC header is ignored for alignment.
            if chars and chars[-1]!=' ':chars.append(' ');mapping.append(i)
            continue
        normalized=unicodedata.normalize('NFKC',c).translate(PUNCT).casefold()
        for n in normalized:
            if n.isspace():
                if chars and chars[-1]==' ':continue
                n=' '
            chars.append(n);mapping.append(i)
    return ''.join(chars),mapping


def exact_typographic_span(text,quote,verified_page_spans=()):
    target,_=canonical(quote)
    source,mapping=canonical(text,pagination=True,verified_page_spans=verified_page_spans)
    target=target.strip()
    if not target:return None
    index=source.find(target)
    if index<0 or source.find(target,index+1)>=0:return None
    start,end=mapping[index],mapping[index+len(target)-1]+1
    return text[start:end],{'start':start,'end':end,'method':'unique_typographic_or_pagination_equivalence'}


def repair(result,text,verified_page_spans=()):
    if not isinstance(result,dict) or not v.FIELDS <= set(result):
        raise ValueError('Required schema fields missing; no offline imputation')
    fixes=[]
    extra=sorted(set(result)-v.FIELDS)
    clean={k:result[k] for k in v.FIELDS}
    if extra:fixes.append({'type':'ignored_extra_json_keys','keys':extra})
    if not isinstance(clean['evidence'],list):raise ValueError('Evidence array invalid')
    evidence=[]
    for q in clean['evidence']:
        if not isinstance(q,str):raise ValueError('Evidence quote invalid')
        loc=v.quote_location(text,q)
        if loc is not None:
            actual=text[loc['start']:loc['end']]
            if actual!=q:fixes.append({'type':'verbatim_source_whitespace_case','model_quote':q,'source_quote':actual,'location':loc})
        else:
            match=exact_typographic_span(text,q,verified_page_spans)
            if match is None:raise ValueError('Quote requires semantic correction; retained unresolved')
            actual,loc=match
            fixes.append({'type':'verbatim_source_typography','model_quote':q,'source_quote':actual,'location':loc})
        evidence.append(actual)
    clean['evidence']=evidence
    locations=v.validate(clean,text)
    return clean,locations,fixes


def offline_recover():
    states,meta=v.prepare()
    by={v.key(s):s for s in states}
    recovered=[];unresolved=[]
    candidates=exception_keys()
    for k in candidates:
        if k not in by:continue
        p=v.cache_file(by[k])
        if not p.exists():continue
        saved=json.loads(p.read_text(encoding='utf-8'))
        if saved['status']!='error':continue
        rawpath=saved.get('recovery_raw_response_file') or saved.get('raw_response_file')
        if not rawpath:continue
        try:
            raw=json.loads((v.ROOT/rawpath).read_text(encoding='utf-8'))
            if raw['choices'][0].get('finish_reason')=='length':raise ValueError('Truncated raw response')
            parsed=json.loads(raw['choices'][0]['message']['content'])
            text=v.texts(by[v.key(saved)])
            clean,locations,fixes=repair(parsed,text)
            if raw.get('model','').lower() not in {v.MODEL.lower(),v.INTENDED_MODEL_VERSION.lower()}:
                raise ValueError('Unexpected raw returned model')
            archive=v.OUT/'recovery_originals'/p.name
            if not archive.exists():v.dump(archive,saved)
            saved.update(result=clean,quote_locations=locations,status='review' if clean['manual_review_needed'] else 'complete',
                         classified_at_utc=v.now(),raw_parsed_result=parsed,offline_recovery=fixes,
                         original_failed_cache=v.rel(archive))
            if saved.get('recovery_raw_response_file'):
                snapshot=saved['recovery_messages_snapshot']
                payload=json.loads((v.ROOT/snapshot).read_text(encoding='utf-8'))
                saved.update(primary_payload_sha256=saved.get('primary_payload_sha256',saved['payload_sha256']),
                             payload_sha256=v.sha(json.dumps(payload,ensure_ascii=False).encode()),
                             messages_snapshot=snapshot,raw_response_file=rawpath,
                             prompt_version=v.prompt.PROMPT_VERSION+f"-validation-recovery{saved.get('recovery_round',1)}")
            saved.pop('error',None)
            v.dump(p,saved)
            recovered.append(dict(ticker=saved['ticker'],cik=saved['cik'],fiscal_year=saved['fiscal_year'],section=saved['section'],
                                  classification=clean['classification'],changes=json.dumps(fixes,ensure_ascii=False),raw_response_file=rawpath))
        except (ValueError,KeyError,TypeError,OSError) as e:
            unresolved.append(dict(ticker=saved['ticker'],cik=saved['cik'],fiscal_year=saved['fiscal_year'],section=saved['section'],reason=str(e)))
    merge_audit(v.OUT/'offline_response_recovery.csv',recovered)
    v.rows(v.OUT/'offline_recovery_unresolved.csv',unresolved)
    v.log(f'Offline recovery: {len(recovered)} recovered; {len(unresolved)} remain unresolved; no paid calls')
    return recovered,unresolved


def exception_keys():
    keys=set()
    with (v.OUT/'request_manifest.jsonl').open(encoding='utf-8') as f:
        for line in f:
            e=json.loads(line)
            if e['status'] in {'validation_or_transport_error','semantic_qa_queued'} or (e['status']=='validated' and e.get('classification_status')=='review'):
                keys.add(v.key(e))
    return keys


def merge_audit(path,rows):
    existing=v.read(path) if path.exists() else []
    by={v.key(r):r for r in existing if 'section' in r}
    by.update({v.key(r):r for r in rows})
    merged=list(by.values())
    fields=list(dict.fromkeys(k for r in merged for k in r))
    v.rows(path,merged,fields or None)


RECOVERY_VERSION=v.prompt.PROMPT_VERSION+'-validation-recovery1'
RECOVERY_SUFFIX='''
VALIDATION RECOVERY REQUEST
The previous response for this same complete section failed validation or retained
a material-review state. Feedback: {feedback}
Recheck the complete supplied text under the same authoritative v2 standard.
Return exactly the required JSON fields. Do not add response_format/type metadata.
Each evidence element must be a contiguous quotation copied directly from this
section. Preserve actual source wording and punctuation. Do not paraphrase, combine
separated sentences or replace source text with a summary. Negative may use an
empty evidence array if there is no relevant evidence. A Positive must retain the
complete C1-C5 source connection. Do not change classification merely to fix a quote.
If implementation evidence consists of developing/establishing a future arrangement,
apply the standard's C3 and future-plan exclusion. Retain null review only when
material ambiguity truly prevents a binary judgment under the supplied standard.
'''

RECOVERY_ROUND2_APPENDIX='''
SECOND AND LAST CORRECTIVE FORMAT REQUEST
For Negative, set evidence=[] and explain the full-section judgment in reason.
For Positive, use the shortest exact contiguous source sentence(s) sufficient to
support the C1-C5 evidence connection. Avoid unnecessary introductory risk quotes.
If a sentence crosses pagination/header artifacts, use separate exact quotes from
each side or select another complete source sentence; do not silently omit source
words or assemble a quote. Copy spelling and punctuation exactly. Retain the same
binary substantive standard and null only for genuinely material ambiguity.
'''


def recovery_payload(row,previous,round_no=None):
    round_no=round_no or row.get('recovery_round',1)
    feedback=previous.get('semantic_qa_feedback') or previous.get('recovery_error') or previous.get('error') or previous.get('result',{}).get('review_reason','Unresolved validation')
    # Feedback describes the actual validation problem, not a desired label.
    suffix=RECOVERY_SUFFIX+(RECOVERY_ROUND2_APPENDIX if round_no==2 else '')
    return build_payload(v.system(),v.user(row,v.texts(row))+suffix.format(feedback=feedback),max_tokens=v.MAX_TOKENS)


def validate_recovery_snapshot(record,actual):
    """Check source/template/parameters and archived feedback independently of
    later changes to which error field is preferred for a subsequent round.
    """
    round_no=record.get('recovery_round',1)
    template=RECOVERY_SUFFIX+(RECOVERY_ROUND2_APPENDIX if round_no==2 else '')
    base=v.user(record,v.texts(record))
    content=actual['messages'][1]['content']
    if not content.startswith(base):return False
    prefix,post=template.split('{feedback}')
    match=re.fullmatch(re.escape(prefix)+r'(.*?)'+re.escape(post),content[len(base):],re.S)
    if not match:return False
    feedback=match.group(1)
    allowed=set();seen=set();path=record.get('original_failed_cache')
    while path and path not in seen:
        seen.add(path)
        old=json.loads((v.ROOT/path).read_text(encoding='utf-8'))
        allowed.update(x for x in [old.get('semantic_qa_feedback'),old.get('recovery_error'),old.get('error'),old.get('result',{}).get('review_reason')] if isinstance(x,str) and x)
        path=old.get('original_failed_cache')
    expected=build_payload(v.system(),base+template.format(feedback=feedback),max_tokens=v.MAX_TOKENS)
    return feedback in allowed and actual==expected


def queue_semantic_source_review():
    """Machine QA queue; retain original model output without inventing a label."""
    states,meta=v.prepare()
    queued=[]
    feedback=("Source-based semantic QA: the cited text refers to safeguards designed to promote ethical AI implementation. "
              "Recheck C3 (established/in force or actually executed) and C4 (identifiable organizational governance mechanism) "
              "against the full section. Distinguish a current disclosed risk control from a general ethical aspiration or design-only claim. "
              "Do not require company-wide coverage, a formal brand, a separately named policy or evidence of effectiveness; these are not v2 requirements. "
              "Do not infer an undisclosed organizational procedure. Resolve by the sole authoritative standard, or retain material ambiguity.")
    for s in states:
        if s['ticker']!='GEHC' or s['fiscal_year'] not in {'2022','2023','2025'} or s['section']!='item1a' or not s['text_available']:continue
        p=v.cache_file(s)
        r=json.loads(p.read_text(encoding='utf-8'))
        if r.get('status')!='complete' or r.get('result',{}).get('classification')!='Positive':continue
        archive=v.OUT/'semantic_qa_originals'/p.name
        if not archive.exists():v.dump(archive,r)
        r.update(status='review',semantic_qa_pending=True,semantic_qa_feedback=feedback,
                 semantic_qa_original_cache=v.rel(archive))
        v.dump(p,r)
        queued.append(dict(cik=s['cik'],ticker=s['ticker'],fiscal_year=s['fiscal_year'],section=s['section'],
                           original_classification='Positive',review_status='machine_semantic_qa',feedback=feedback,
                           original_cache=v.rel(archive)))
        with (v.OUT/'request_manifest.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(dict(s,status='semantic_qa_queued',timestamp_utc=v.now(),prompt_version=v.prompt.PROMPT_VERSION,
                                    feedback=feedback),ensure_ascii=False)+'\n')
    merge_audit(v.OUT/'semantic_source_review_manifest.csv',queued)
    return queued


def retry_recovery(states,workers=16,limit=None,round_no=1):
    """One corrective request per unresolved section, preserving every old response."""
    if round_no not in {1,2}:raise ValueError('At most two corrective rounds')
    version=v.prompt.PROMPT_VERSION+f'-validation-recovery{round_no}'
    suffix=RECOVERY_SUFFIX+(RECOVERY_ROUND2_APPENDIX if round_no==2 else '')
    suffix_name='validation_retry_user_suffix_template.txt' if round_no==1 else 'validation_retry_user_suffix_template_round2.txt'
    (v.OUT/suffix_name).write_text(suffix,encoding='utf-8')
    config=load_config(v.prior._env_file())
    config_name='recovery_llm_config.json' if round_no==1 else 'recovery_round2_llm_config.json'
    v.dump(v.OUT/config_name,dict(v.prepare()[1]['llm_config'],
            prompt_version=version,corrective_requests_per_section=1,maximum_corrective_rounds=2,workers=workers,
            original_system_prompt_unchanged=True,original_standard_unchanged=True))
    todo=[]
    exceptions=exception_keys()
    for s in states:
        if not s['text_available']:continue
        if v.key(s) not in exceptions:continue
        p=v.cache_file(s)
        if p.exists():
            saved=json.loads(p.read_text(encoding='utf-8'))
            prior_round=saved.get('recovery_round',1 if saved.get('recovery_attempted') else 0)
            if saved['status'] in {'error','review'} and prior_round<round_no:
                todo.append((s,p,saved))
    if limit is not None:todo=todo[:limit]
    lock=threading.Lock()
    def perform(task):
        row,path,previous=task
        payload=recovery_payload(row,previous,round_no)
        digest=v.sha(json.dumps(payload,ensure_ascii=False).encode())
        pp=v.OUT/'requests'/f'{digest}.json'
        v.dump(pp,payload)
        group=uuid.uuid4().hex;active={'attempt':0,'raw':None}
        def observe(event):
            if event['status']=='started':active['attempt']=event['attempt']
            e={k:row[k] for k in ['cik','ticker','fiscal_year','section','input_file','input_sha256']}
            e.update(timestamp_utc=v.now(),request_id=f"{group}_{active['attempt']}",prompt_version=version,
                     model=v.MODEL,messages_snapshot=v.rel(pp),payload_sha256=digest,
                     phase='validation_recovery',**event)
            if event['status']=='response_received':e['raw_response_file']=active['raw']
            with lock:
                with (v.OUT/'request_manifest.jsonl').open('a',encoding='utf-8') as f:
                    f.write(json.dumps(e,ensure_ascii=False)+'\n')
        def raw(response):
            rp=v.OUT/'responses'/f"{group}_{active['attempt']}.json"
            v.dump(rp,response);active['raw']=v.rel(rp)
        archive=v.OUT/'recovery_originals'/(f'pre_corrective_round{round_no}_'+path.name)
        if not archive.exists():v.dump(archive,previous)
        try:
            result,metadata=chat_json(payload['messages'][0]['content'],payload['messages'][1]['content'],config=config,
                                     max_tokens=v.MAX_TOKENS,attempt_observer=observe,response_observer=raw)
            clean,locations,fixes=repair(result,v.texts(row))
            if metadata['returned_model'].lower() not in {v.MODEL.lower(),v.INTENDED_MODEL_VERSION.lower()}:
                raise ValueError('Unexpected returned model')
            record=dict(row,result=clean,metadata=metadata,quote_locations=locations,
                        status='review' if clean['manual_review_needed'] else 'complete',classified_at_utc=v.now(),
                        prompt_version=version,model=v.MODEL,payload_sha256=digest,
                        primary_payload_sha256=previous.get('primary_payload_sha256',previous['payload_sha256']),
                        messages_snapshot=v.rel(pp),raw_response_file=active['raw'],raw_parsed_result=result,
                        offline_recovery=fixes,recovery_attempted=True,recovery_round=round_no,original_failed_cache=v.rel(archive),
                        validation_requests=previous.get('validation_requests',0)+1)
            v.dump(path,record)
            observe({'status':'validated','classification_status':record['status'],'cache_file':v.rel(path)})
            return record
        except Exception as exc:
            record=dict(previous,recovery_attempted=True,recovery_round=round_no,recovery_error=f'{type(exc).__name__}: {exc}',
                        recovery_raw_response_file=active['raw'],recovery_messages_snapshot=v.rel(pp),
                        original_failed_cache=v.rel(archive))
            v.dump(path,record)
            observe({'status':'validation_or_transport_error','error':record['recovery_error'],'raw_response_file':active['raw']})
            return record
    records=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i,f in enumerate(as_completed([pool.submit(perform,t) for t in todo]),1):
            r=f.result();records.append(r)
            if i%10==0 or i==len(todo):v.log(f'Corrective recovery: {i}/{len(todo)}; binary={sum(r["status"]=="complete" for r in records)}')
    merge_audit(v.OUT/'corrective_recovery_summary.csv',[
        dict(cik=r['cik'],ticker=r['ticker'],fiscal_year=r['fiscal_year'],section=r['section'],status=r['status'],
             classification=r.get('result',{}).get('classification'),error=r.get('recovery_error',''),
             round_no=round_no,raw_response_file=r.get('recovery_raw_response_file',r.get('raw_response_file',''))) for r in records])
    return records
