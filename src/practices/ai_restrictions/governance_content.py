"""Evidence-preserving exploratory and frozen-codebook content analysis.

The output bundle is explicitly requested by the researcher. Resumable API state
and human queues stay in data/interim; no original inputs or binary outputs change.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
import threading
import time
import urllib.error
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .llm.client import build_payload, chat_json, load_config, _transport
from .llm import content_analysis_prompt as prompt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'outputs/full_universe_implemented_internal_ai_governance_v2'
OUT = ROOT / 'outputs/implemented_ai_governance_content_analysis'
STATE = ROOT / 'data/interim/classifications/implemented_ai_governance_content_analysis/v1'
DIMS = ('practices', 'motivations', 'visions')
RUN_ID = 'implemented-ai-governance-content-v1-20261018'
LOCK = threading.Lock()
STOP = threading.Event()


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def csvout(path, data, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for r in data for k in r))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in data:
            w.writerow({k: canonical(v) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def log(obj):
    print(canonical(obj), flush=True)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    paths = [BASE / n for n in ('combined_firm_year_v2_panel.csv', 'positive_evidence_audit.csv',
             'item1a_v2_classification_results.csv', 'item7_v2_classification_results.csv',
             'positive_evidence_contexts.jsonl', 'llm_config.json', 'delivery_qa.json')]
    paths += [ROOT / 'docs/implemented_internal_ai_governance_v2.md']
    paths += [ROOT / f'data/raw/universe/sp{s}.csv' for s in ('500', '400', '600')]
    protected = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths}
    positive = [r for r in rows(BASE/'combined_firm_year_v2_panel.csv')
                if r['implemented_internal_ai_governance_v2'] == '1']
    assert len({(r['cik'], r['fiscal_year']) for r in positive}) == len(positive)
    keys = {(r['cik'], r['fiscal_year']) for r in positive}
    sections = rows(BASE/'positive_evidence_audit.csv')
    assert {(r['cik'], r['fiscal_year']) for r in sections} == keys
    assert len({(r['cik'], r['fiscal_year'], r['section']) for r in sections}) == len(sections)
    # Sector metadata from the same saved sampling frame, never current web membership.
    sectors = {}
    for size in ('500', '400', '600'):
        for r in rows(ROOT/f'data/raw/universe/sp{size}.csv'):
            sectors[r['Symbol'].replace('.', '-')] = r['GICS Sector']
    counts = Counter((r['cik'], r['fiscal_year']) for r in sections)
    units = []
    normalized_restored = 0
    for r in sections:
        assert r['classification'] == 'Positive' and r['classification_status'] == 'complete'
        path = ROOT/r['input_file']
        b = path.read_bytes()
        assert digest(b) == r['input_sha256'], r['input_file']
        protected[r['input_file']] = digest(b)
        # Match the binary workflow's read_text universal-newline character space.
        text = path.read_text(encoding='utf-8-sig')
        evidence, locs = json.loads(r['evidence']), json.loads(r['evidence_locations'])
        assert len(evidence) == len(locs)
        for i, (q, loc) in enumerate(zip(evidence, locs), 1):
            start, end = int(loc['start']), int(loc['end'])
            original_q=q
            source_q=text[start:end]
            if source_q != q:
                assert ' '.join(source_q.split()).casefold() == ' '.join(q.split()).casefold(), (r['ticker'],i,'substantive quote mismatch')
                normalized_restored += 1
                q=source_q
            lo, hi = max(0, start-1100), min(len(text), end+1100)
            units.append(dict(evidence_id=f"{r['cik']}_FY{r['fiscal_year']}_{r['section']}_E{i:02d}",
                cik=r['cik'], ticker=r['ticker'], company_name=r['company_name'],
                fiscal_year=int(r['fiscal_year']), section=r['section'],
                accession_number=r['accession_number'], filing_date=r['filing_date'],
                sector=sectors.get(r['ticker'].replace('.', '-'), 'Unknown'),
                input_file=r['input_file'], input_sha256=r['input_sha256'],
                evidence=q, binary_original_evidence=original_q,
                binary_location_method=loc.get('method',''),
                source_span_restored=(original_q!=q), evidence_start=start, evidence_end=end,
                context_start=lo, context_end=hi, source_context=text[lo:hi],
                both_sections_positive=counts[(r['cik'],r['fiscal_year'])] == 2,
                binary_prompt_version=r['prompt_version'], binary_classification='Positive'))
    if (STATE/'protected_inputs.json').exists():
        assert read(STATE/'protected_inputs.json') == protected, 'Input drift; use a new run version'
    else:
        dump(STATE/'protected_inputs.json', protected)
    dump(STATE/'evidence_units.json', units)
    csvout(STATE/'evidence_source_index.csv', units)
    firm = {}
    for u in units:
        k = (u['cik'],u['fiscal_year'])
        firm.setdefault(k, dict(cik=k[0], fiscal_year=k[1], ticker=u['ticker'],
            sector=u['sector'], both_sections_positive=u['both_sections_positive'],
            sections=set(), evidence_characters=0))
        firm[k]['sections'].add(u['section'])
        firm[k]['evidence_characters'] += len(u['evidence'])
    fs = list(firm.values())
    lengths = sorted(f['evidence_characters'] for f in fs)
    for f in fs:
        f['length_bin'] = min(3, sum(f['evidence_characters'] > lengths[int(len(lengths)*q)] for q in (.25,.5,.75)))
        f['sections'] = '+'.join(sorted(f['sections']))
    # Purposeful maximum-variation sample, reproducible seeded tie-breaking.
    # Census of early years; both-positive census; fill rare strata with diversity.
    selected = {(f['cik'], f['fiscal_year']) for f in fs
                if f['fiscal_year'] <= 2022 or f['both_sections_positive']}
    rng = random.Random(42)
    rng.shuffle(fs)
    def score(f):
        chosen = [v for v in fs if (v['cik'],v['fiscal_year']) in selected]
        n = lambda field: sum(v[field] == f[field] for v in chosen)
        return (5/(1+n('fiscal_year')) + 5/(1+n('sector')) + 4/(1+n('sections'))
                + 2/(1+n('length_bin')) + 2/(1+sum(v['cik']==f['cik'] for v in chosen)))
    while len(selected) < min(50, len(fs)):
        f = max((v for v in fs if (v['cik'],v['fiscal_year']) not in selected), key=score)
        selected.add((f['cik'],f['fiscal_year']))
    sample = sorted([f for f in fs if (f['cik'],f['fiscal_year']) in selected], key=lambda f:(f['fiscal_year'],f['ticker']))
    csvout(OUT/'exploration_sample.csv', sample)
    dump(STATE/'exploration_keys.json', [list(k) for k in sorted(selected)])
    csvout(OUT/'evidence_source_index.csv', [{k:v for k,v in u.items() if k!='source_context'} for u in units])
    config = read(BASE/'llm_config.json')
    config.update(prompt_version=prompt.VERSION, full_text_input=False,
        input_policy='Positive anchor plus 1100 source characters per side; immutable source spans',
        official_model_version_on_20261018='DeepSeek-V4.1-Flash-1017',
        model_alias_drift_note='Same requested model alias as binary workflow; provider upgraded alias. Returned model logged per response.',
        workers=16, validation_request_limit=2, run_id=RUN_ID,
        retry_backoff_seconds=[2,4,8], max_tokens=16384,
        state_directory=str(STATE.relative_to(ROOT)).replace('\\','/'))
    dump(OUT/'llm_config.json', config)
    for filename, content in [('open_coding_system_prompt.txt', prompt.OPEN_SYSTEM),
        ('codebook_synthesis_system_prompt.txt', prompt.SYNTHESIS_SYSTEM),
        ('system_prompt.txt', prompt.CODING_SYSTEM),
        ('user_prompt_template.txt', 'FROZEN CODEBOOK: {codebook_json}\nEVIDENCE UNIT: {evidence_unit_json}\nReturn the required JSON for this evidence_id.'),
        ('open_coding_user_prompt_template.txt', 'OPEN CODING: {firm_year_evidence_units_json}')]:
        (OUT/filename).write_text(content,encoding='utf-8')
    shutil.copyfile(ROOT/'docs/implemented_internal_ai_governance_v2.md', OUT/'binary_standard_snapshot.md')
    inv = dict(positive_firm_years=len(positive), positive_sections=len(sections), evidence_units=len(units),
        unique_firms=len({r['cik'] for r in positive}), both_positive_firm_years=sum(v==2 for v in counts.values()),
        sections=dict(Counter(r['section'] for r in sections)), annual=dict(Counter(r['fiscal_year'] for r in positive)),
        evidence_by_section=dict(Counter(u['section'] for u in units)),
        missing_sources=0, source_hash_failures=0, original_quote_failures=0,
        binary_normalized_quotes_restored_to_exact_source=normalized_restored,
        exploration_firm_years=len(sample), exploration_evidence=sum((u['cik'],u['fiscal_year']) in selected for u in units),
        exploration_annual=dict(Counter(f['fiscal_year'] for f in sample)),
        exploration_sector=dict(Counter(f['sector'] for f in sample)),
        exploration_section_patterns=dict(Counter(f['sections'] for f in sample)),
        unknown_sector_firm_years=sum(f['sector']=='Unknown' for f in fs), created_utc=now())
    dump(OUT/'data_inventory.json', inv)
    (OUT/'data_inventory.md').write_text(f'''# Data Inventory

正式来源：`outputs/full_universe_implemented_internal_ai_governance_v2/`。标准：
`docs/implemented_internal_ai_governance_v2.md`；本次未重新判断 Binary Positive。

- Positive firm-year：{len(positive)}；独立公司：{inv['unique_firms']}。
- Positive 章节：{len(sections)}，章节分布：{inv['sections']}。
- 原始 Evidence：{len(units)}，分布：{inv['evidence_by_section']}。
- 双章节 Positive firm-year：{inv['both_positive_firm_years']}；全部原文可用。
- 原文文件哈希逐一匹配；{len(units)-normalized_restored} 条原始引文精确匹配，
  {normalized_restored} 条原流程已标记 normalized_whitespace_case 的引文在验证仅有空白/大小写差异后，
  在本次派生输入中恢复为原始 offset 对应的精确原文；同时保留 Binary 原始引文。实质不匹配为 0。
- 年度 Positive 数：{inv['annual']}。
- 探索样本：{len(sample)} firm-years、{inv['exploration_evidence']} Evidence；年份分布 {inv['exploration_annual']}。
- 探索行业分布：{inv['exploration_sector']}；章节组合 {inv['exploration_section_patterns']}。

样本采用 seed=42、最大差异目的抽样，全部纳入 FY2020–2022 和双章节 Positive；
其余按年份、固定历史 GICS 行业、章节组合、证据总长度四分位和公司多样性补足 50。
该探索样本用于发现主题，不用于加权估计。行业来自项目保存的 sp500/sp400/sp600.csv，
未知行业保持 Unknown（全样本 {inv['unknown_sector_firm_years']} firm-years）。

使用文件：combined_firm_year_v2_panel.csv、positive_evidence_audit.csv、
item1a_v2_classification_results.csv、item7_v2_classification_results.csv、
positive_evidence_contexts.jsonl、llm_config.json、delivery_qa.json。
本次从原始 Item TXT 按字符位置重建每条证据及左右各 1100 字符的上下文。
只编码 Positive 章节内这些治理证据及可关联上下文；未重新搜索整章新增治理段落。
因此 Not Disclosed 的范围是已选证据和有界上下文，不能外推整份 10-K。

证据路径、哈希、accession、原文和位置见 evidence_source_index.csv；
完整上下文和原始输入保护哈希位于 `{STATE.relative_to(ROOT).as_posix()}`。
位置沿用 Binary Workflow 的 Python read_text 换行标准化 Unicode 字符空间，
0-based [start,end)，不作字节位置或原始 HTML 页码解释；SHA-256 始终使用原始字节。

正式 Binary 标准及输出全部只读。独立研究结果写入用户指定 outputs 目录；
API 原始响应、请求、日志、缓存和待人工审核队列保存在 data/interim。
所有结果均为 LLM 主题编码，人工决定另行保存，不伪装为人工验证。
''', encoding='utf-8')
    dump(OUT/'run_manifest.json', dict(run_id=RUN_ID, stage='prepared', prepared_utc=now(),
        protected_inputs=str((STATE/'protected_inputs.json').relative_to(ROOT)).replace('\\','/'),
        input_digest=digest(canonical(protected).encode()), state_directory=STATE.relative_to(ROOT).as_posix(),
        outputs_directory=OUT.relative_to(ROOT).as_posix(), version=prompt.VERSION))
    snap = OUT/'code_snapshot'
    snap.mkdir(exist_ok=True)
    for p in [Path(__file__), ROOT/'src/ai_restrictions/llm/content_analysis_prompt.py',
              ROOT/'src/ai_restrictions/llm/client.py', ROOT/'scripts/43_analyze_governance_content.py']:
        shutil.copyfile(p, snap/p.name)
    log(inv)


def unit_input(u, include_primary_context=False):
    result={k:u[k] for k in ('evidence_id','cik','ticker','fiscal_year','section',
        'evidence','evidence_start','evidence_end','context_start','context_end','source_context',
        'context_blocks') if k in u}
    if 'context_blocks' in result and not include_primary_context: result.pop('source_context',None)
    return result


def supplement(workers):
    """Read same-source companion evidence before resolving exploration boundary cases."""
    units=read(STATE/'evidence_units.json')
    original=read(STATE/'open_coding_results.json')
    backup=STATE/'open_coding_results_before_context_v2.json'
    if not backup.exists(): dump(backup,original)
    else: original=read(backup)
    sections=defaultdict(list)
    for u in units: sections[(u['cik'],u['fiscal_year'],u['section'])].append(u)
    for us in sections.values():
        source=ROOT/us[0]['input_file']
        assert sha(source)==us[0]['input_sha256']
        text=source.read_text(encoding='utf-8-sig')
        ranges=sorted((u['context_start'],u['context_end']) for u in us)
        merged=[]
        for lo,hi in ranges:
            if merged and lo<=merged[-1][1]: merged[-1][1]=max(hi,merged[-1][1])
            else: merged.append([lo,hi])
        blocks=[dict(start=lo,end=hi,source_context=text[lo:hi]) for lo,hi in merged]
        for u in us: u['context_blocks']=blocks
    dump(STATE/'evidence_units.json',units)
    byid={u['evidence_id']:u for u in units}
    target_keys={(byid[x['evidence_id']]['cik'],byid[x['evidence_id']]['fiscal_year'])
        for x in original if x['review_flag'] or x['uncodable']}
    groups=defaultdict(list)
    for u in units:
        if (u['cik'],u['fiscal_year']) in target_keys: groups[(u['cik'],u['fiscal_year'])].append(u)
    def process(k,us):
        def validate(r):
            obs=r.get('observations',[])
            if len(obs)!=len(us) or {x['evidence_id'] for x in obs}!={u['evidence_id'] for u in us}: raise ValueError('Supplement coverage mismatch')
            for x in obs: validate_observation(x,byid[x['evidence_id']])
        return call('open_context_v2',f'{k[0]}_FY{k[1]}',prompt.OPEN_SYSTEM,
            'OPEN CODING WITH SAME-CHAPTER SOURCE CONTEXT BLOCKS: '+canonical([unit_input(u,include_primary_context=True) for u in us]),validate)
    output={x['evidence_id']:x for x in original}
    done=0; failed=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(process,k,us):k for k,us in groups.items()}
        for f in as_completed(tasks):
            k=tasks[f]; s=f.result(); done+=1
            if s['status']=='complete': output.update({x['evidence_id']:x for x in s['result']['observations']})
            else: failed.append(k)
            log(dict(stage='context_supplement',done=done,total=len(groups),key=k,status=s['status']))
    if failed: raise RuntimeError('Supplement failures '+repr(failed))
    final=[output[x['evidence_id']] for x in original]
    for x in final: validate_observation(x,byid[x['evidence_id']])
    dump(STATE/'open_coding_results.json',final)
    csvout(OUT/'open_coding_results.csv',final)
    dump(OUT/'context_supplement_manifest.json',dict(stage='exploration_before_freeze',
        revised_input_version='same-chapter-context-v2',supplemented_firm_years=len(groups),
        supplemented_evidence=sum(len(us) for us in groups.values()),
        sample_membership_changed=False,initial_flagged_evidence=sum(x['review_flag'] for x in original),
        supplemented_flagged_evidence=sum(x['review_flag'] for x in final),
        reason='Initial open coding flagged fragmented risk/scope anchors and current-review vs future-adoption ambiguity; read same-chapter companion source spans before codebook freeze.',
        original_results=backup.relative_to(ROOT).as_posix(),completed_utc=now()))
    for filename,content in [('open_coding_system_prompt.txt',prompt.OPEN_SYSTEM),('system_prompt.txt',prompt.CODING_SYSTEM)]:
        (OUT/filename).write_text(content,encoding='utf-8')
    if (OUT/'codebook_draft.json').exists() and not (OUT/'codebook_draft_before_context_v2.json').exists():
        shutil.copyfile(OUT/'codebook_draft.json',OUT/'codebook_draft_before_context_v2.json')
    cfg=read(OUT/'llm_config.json'); cfg['input_policy']='Focal evidence plus merged continuous context blocks around ALL companion Positive evidence in the same chapter, 1100 characters each side; no cross-block quote stitching.'
    dump(OUT/'llm_config.json',cfg)
    with (OUT/'data_inventory.md').open('a',encoding='utf-8') as f:
        f.write('\n探索补充上下文：发现组合证据片段后，对初次标记的 '+str(len(groups))+' 个原样本 firm-year 补充开放编码；'
            '所有编码输入均保留同一 Positive 章节的全部合格 Evidence 周边连续上下文块，重叠块合并。'
            '未重新检索整章新增主题，样本和原始证据不变；引文必须完整落于单一连续块。'
            '原初开放编码、补充结果和草案均有独立版本记录，见 context_supplement_manifest.json。\n')


def call(stage, ident, system, user, validator, max_tokens=16384):
    """Cached validated successes; exact payloads and all received attempts retained."""
    payload = build_payload(system, user, max_tokens=max_tokens)
    signature = digest(canonical(payload).encode())
    cache = STATE/'cache'/stage/(ident+'.json')
    if cache.exists():
        saved = read(cache)
        assert saved['payload_sha256'] == signature, 'Prompt/input drift on resume'
        if saved['status'] == 'complete':
            validator(saved['result'])
            return saved
    if STOP.is_set():
        return dict(status='not_submitted', error='billing circuit breaker')
    cfg = load_config(ROOT/'.env')
    start = time.monotonic()
    # Finite corrective retries with no changes to thematic rules.
    errors=[]
    prior_n=len(list((STATE/'requests'/stage).glob(ident+'__*.json'))) if (STATE/'requests'/stage).exists() else 0
    if prior_n >= 4:
        return read(cache) if cache.exists() else dict(status='failed', error='total request limit')
    for validation_attempt in range(min(2,4-prior_n)):
        if STOP.is_set(): break
        suffix = '' if not errors else '\nValidation correction required: '+errors[-1]+'. Return corrected exact JSON; preserve the same codebook and original text.'
        actual_user=user+suffix
        request_id=ident+'__'+str(prior_n+validation_attempt+1)
        request_file=STATE/'requests'/stage/(request_id+'.json')
        actual_payload=build_payload(system,actual_user,max_tokens=max_tokens)
        dump(request_file,dict(payload=actual_payload, payload_sha256=digest(canonical(actual_payload).encode()), created_utc=now(), stage=stage))
        response_i=[0]
        def event(e):
            row=dict(stage=stage,evidence_or_batch_id=ident,request_id=request_id,time_utc=now(),**e)
            with LOCK:
                with (STATE/'request_manifest.jsonl').open('a',encoding='utf-8') as f:
                    f.write(canonical(row)+'\n')
        def response(r):
            response_i[0]+=1
            dump(STATE/'responses'/stage/(request_id+f'__{response_i[0]}.json'),r)
        def transport(url,body,headers,timeout):
            try:
                return _transport(url,body,headers,timeout)
            except urllib.error.HTTPError as exc:
                # Error bodies are diagnostic data; never include request headers.
                error_body=exc.read().decode('utf-8',errors='replace')
                dump(STATE/'responses'/stage/(request_id+f'__http_error_{response_i[0]}.json'),
                    dict(http_status=exc.code,error_body=error_body,received_utc=now()))
                raise
        try:
            result, meta=chat_json(system,actual_user,config=cfg,max_tokens=max_tokens,
                                  attempt_observer=event,response_observer=response,transport=transport)
            # Parsed raw output retained even if semantic/quote validation fails.
            dump(STATE/'parsed'/stage/(request_id+'.json'),result)
            validator(result)
            saved=dict(status='complete',result=result,metadata=meta,payload_sha256=signature,
                       validated_utc=now(),elapsed_seconds=time.monotonic()-start,prior_validation_errors=errors)
            dump(cache,saved)
            return saved
        except Exception as exc:
            error=f'{type(exc).__name__}: {exc}'
            errors.append(error)
            event(dict(status='validation_or_transport_failure',error=error))
            if 'HTTP 402' in error:
                STOP.set()
                break
            if any(f'HTTP {code}' in error for code in (400,401,403)): break
    saved=dict(status='failed',payload_sha256=signature,errors=errors,elapsed_seconds=time.monotonic()-start)
    dump(cache,saved)
    return saved


def exact_quote(q, u):
    blocks=u.get('context_blocks') or [dict(start=u['context_start'],source_context=u['source_context'])]
    if not isinstance(q,str) or len(q.strip()) < 8 or not any(q in b['source_context'] for b in blocks):
        raise ValueError(f'Quote not exact in supplied source context for {u["evidence_id"]}: {str(q)[:100]!r}')
    # All matching source locations are retained; no ambiguous first-hit assertion.
    locations=set()
    for b in blocks:
        pos=0
        while True:
            pos=b['source_context'].find(q,pos)
            if pos < 0: break
            locations.add((b['start']+pos,b['start']+pos+len(q)))
            pos+=1
    return [dict(start=a,end=b) for a,b in sorted(locations)]


def validate_observation(r,u,codebook=None):
    if not isinstance(r,dict) or r.get('evidence_id') != u['evidence_id']:
        raise ValueError('Missing or wrong evidence_id')
    for key in ('uncodable','review_flag'):
        if type(r.get(key)) is not bool: raise ValueError('Missing boolean '+key)
    if not isinstance(r.get('review_reason'),str): raise ValueError('Missing review_reason')
    if r['review_flag'] and not r['review_reason'].strip(): raise ValueError('Flagged review requires reason')
    for dim in DIMS:
        values=r.get(dim)
        if not isinstance(values,list): raise ValueError('Missing list '+dim)
        seen=set()
        for v in values:
            field='category_id' if codebook else 'theme'
            if not isinstance(v.get(field),str) or not v[field].strip(): raise ValueError('Missing '+field)
            if v[field] in seen: raise ValueError('Duplicate label')
            seen.add(v[field])
            if codebook and v[field] not in {c['id'] for c in codebook['categories'] if c['dimension']==dim}:
                raise ValueError('Unknown or wrong-dimension category '+v[field])
            exact_quote(v.get('quote'),u)
            if not isinstance(v.get('explanation'),str) or not v['explanation'].strip(): raise ValueError('Missing explanation')
            if dim!='practices':
                if v.get('explicitness') not in ('Explicit','Implicit'): raise ValueError('Missing explicitness')
                exact_quote(v.get('relationship_quote'),u)
        if dim!='practices':
            status=r.get('motivation_status' if dim=='motivations' else 'vision_status')
            if status not in ('Explicit','Implicit','Mixed','Not Disclosed','Uncertain'): raise ValueError('Invalid dimension status')
            types={v['explicitness'] for v in values}
            expected='Mixed' if len(types)>1 else (next(iter(types)) if types else 'Not Disclosed')
            if status not in (expected,'Uncertain'): raise ValueError('Inconsistent dimension status')
            if status=='Uncertain' and not r['review_flag']: raise ValueError('Uncertain requires review')
    if r['uncodable'] and not r['review_flag']: raise ValueError('Uncodable requires review')
    if not r['practices'] and not r['review_flag']: raise ValueError('No implemented practice; review required')
    if codebook:
        if not isinstance(r.get('emerging_themes'),list): raise ValueError('Missing emerging_themes')
        for e in r['emerging_themes']:
            if e.get('dimension') not in DIMS or not e.get('theme') or not e.get('explanation'): raise ValueError('Invalid emerging theme')
            exact_quote(e.get('quote'),u)
            if e['dimension'] in ('motivations','visions'):
                sk='motivation_status' if e['dimension']=='motivations' else 'vision_status'
                if r[sk]!='Uncertain': raise ValueError('Emerging motive or vision must retain Uncertain status')
        if r['emerging_themes'] and not r['review_flag']: raise ValueError('Emerging theme requires review')


def open_coding(workers):
    units=read(STATE/'evidence_units.json')
    selected={tuple(k) for k in read(STATE/'exploration_keys.json')}
    batches=defaultdict(list)
    for u in units:
        if (u['cik'],u['fiscal_year']) in selected:
            batches[(u['cik'],u['fiscal_year'])].append(u)
    def process(k, us):
        def validate(r):
            obs=r.get('observations',[])
            if len(obs)!=len(us) or {o['evidence_id'] for o in obs}!={u['evidence_id'] for u in us}:
                raise ValueError('Open coding evidence coverage mismatch')
            byid={u['evidence_id']:u for u in us}
            for o in obs: validate_observation(o,byid[o['evidence_id']])
        return call('open',f'{k[0]}_FY{k[1]}',prompt.OPEN_SYSTEM,
            'OPEN CODING: '+canonical([unit_input(u) for u in us]),validate)
    # Four real firms gate subsequent exploration calls.
    ordered=sorted(batches)
    pilot=ordered[:4]
    for k in pilot:
        s=process(k,batches[k]); log(dict(stage='open_pilot',key=k,status=s['status']))
        if s['status']!='complete': raise RuntimeError('Open coding pilot failed; inspect saved state')
    done=4
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(process,k,batches[k]):k for k in ordered[4:]}
        for future in as_completed(tasks):
            s=future.result(); done+=1
            log(dict(stage='open',done=done,total=len(ordered),status=s['status'],key=tasks[future]))
    failures=[]; output=[]
    for k,us in batches.items():
        p=STATE/'cache/open'/f'{k[0]}_FY{k[1]}.json'
        s=read(p) if p.exists() else {}
        if s.get('status')!='complete': failures.append(k)
        else: output.extend(s['result']['observations'])
    dump(STATE/'open_coding_results.json',output)
    if failures: raise RuntimeError(f'Open coding failed observations {failures}')
    csvout(OUT/'open_coding_results.csv',output)
    log(dict(stage='open_complete',firm_years=len(batches),evidence=len(output)))


def synthesize():
    obs=read(STATE/'open_coding_results.json')
    units={u['evidence_id']:u for u in read(STATE/'evidence_units.json')}
    def validate(cb):
        if not isinstance(cb.get('categories'),list) or not cb.get('derivation'): raise ValueError('Missing codebook')
        ids=set()
        for c in cb['categories']:
            for k in ('id','dimension','name','name_zh','definition','inclusion','exclusion','distinction'):
                if not isinstance(c.get(k),str) or not c[k].strip(): raise ValueError('Missing codebook field '+k)
            if c['dimension'] not in DIMS or c['id'] in ids: raise ValueError('Invalid category identity')
            ids.add(c['id'])
            if not c.get('examples'): raise ValueError('Missing codebook example')
            for e in c['examples']: exact_quote(e['quote'],units[e['evidence_id']])
    (OUT/'codebook_synthesis_system_prompt.txt').write_text(prompt.SYNTHESIS_SYSTEM,encoding='utf-8')
    cfg=read(OUT/'llm_config.json')
    cfg.update(synthesis_max_tokens=65536,
        synthesis_setting_exception='Original 16384 limit exhausted by reasoning and truncated output; interrupted remaining identical retries. Only synthesis budget increased; evidence coding remains 16384.',
        synthesis_json_format_correction='Explicit JSON instruction added after initial HTTP 400; earlier request/response provenance retained.')
    dump(OUT/'llm_config.json',cfg)
    ident='codebook_context_v2' if (OUT/'context_supplement_manifest.json').exists() else 'codebook_draft_json_v1'
    result=call('synthesis',ident,prompt.SYNTHESIS_SYSTEM,
        canonical(dict(observations=obs)),validate,max_tokens=65536)
    if result['status']!='complete': raise RuntimeError('Codebook synthesis failed')
    dump(OUT/'codebook_draft.json',result['result'])
    codebook_markdown(result['result'],frozen=False)
    log(dict(stage='codebook_draft',categories=[(c['id'],c['name']) for c in result['result']['categories']]))


def codebook_markdown(cb,frozen):
    units={u['evidence_id']:u for u in read(STATE/'evidence_units.json')}
    lines=['# Inductive Content Codebook v1', '',
        '状态：'+('Frozen；全样本编码使用该 JSON SHA-256，改变规则须建立新版本。' if frozen else 'Draft；尚未开展全样本编码。'),'',
        '归纳过程：50 个最大差异 firm-year，先逐证据 DeepSeek Open Coding，补充组合证据上下文，再综合同义主题；研究助手检查定义、相邻类别与代表引文后冻结。独立人工复核尚未开展。',
        '维度相互独立；多标签。实践仅限已建立/执行的机制。动机和目标需要与具体治理存在文本关系。',
        'Explicit：直接陈述原因、目的或职责目标；Implicit：有清楚语义联系但未直接表述。一般风险或创新描述的邻接不足以建立关系。',
        'Not Disclosed：在该条证据与有界上下文中未披露。Uncertain、uncodable、失败分别保留。Responsible AI 政策名称本身不足以推断目标。',
        '相同 firm-year、相同类别跨 Evidence/Item 去重；显式与隐式同时存在时，主分类 Explicit 优先，原始二者均保留。',
        '代码覆盖不足的新主题记录 Emerging Theme 并进入复核，不自动修改 Codebook。','',cb['derivation'],'']
    for c in cb['categories']:
        lines += [f"## {c['id']} {c['name']}（{c['name_zh']}）",'',
            f"Dimension: {c['dimension']}",'',f"Definition: {c['definition']}",'',
            f"Inclusion: {c['inclusion']}",'',f"Exclusion: {c['exclusion']}",'',
            f"Distinction: {c['distinction']}",'']
        for e in c['examples']:
            u=units[e['evidence_id']]
            lines += [f"{u['ticker']} FY{u['fiscal_year']} {u['section']}，{e['evidence_id']}：",'',f"> {e['quote']}",'']
    lines += ['## Consolidation notes','']+cb.get('consolidation_notes',[])+['','## Minority themes','']+cb.get('minority_theme_notes',[])
    (OUT/('codebook.md' if frozen else 'codebook_draft.md')).write_text('\n'.join(lines),encoding='utf-8')


def freeze():
    cb=read(OUT/'codebook_draft.json')
    target=OUT/'codebook.json'
    if target.exists(): assert read(target)==cb, 'Frozen codebook cannot be changed in place'
    else: dump(target,cb)
    codebook_markdown(cb,True)
    meta=read(OUT/'run_manifest.json')
    meta.update(stage='codebook_frozen',codebook_sha256=sha(target),frozen_utc=meta.get('frozen_utc',now()),
        freeze_review='Research assistant inspected category definitions, quote provenance and neighboring-category boundaries; no independent human reliability study.')
    dump(OUT/'run_manifest.json',meta)
    schemas={}
    for dim in DIMS:
        properties=dict(category_id={'type':'string','enum':[c['id'] for c in cb['categories'] if c['dimension']==dim]},
            quote={'type':'string','minLength':8},explanation={'type':'string','minLength':1})
        required=list(properties)
        if dim!='practices':
            properties.update(explicitness={'enum':['Explicit','Implicit']},relationship_quote={'type':'string','minLength':8})
            required += ['explicitness','relationship_quote']
        schemas[dim]={'type':'array','items':{'type':'object','properties':properties,'required':required}}
    properties=dict(evidence_id={'type':'string','minLength':1},**schemas,
        motivation_status={'enum':['Explicit','Implicit','Mixed','Not Disclosed','Uncertain']},
        vision_status={'enum':['Explicit','Implicit','Mixed','Not Disclosed','Uncertain']},
        uncodable={'type':'boolean'},review_flag={'type':'boolean'},review_reason={'type':'string'},
        emerging_themes={'type':'array','items':{'type':'object','required':['dimension','theme','quote','explanation'],
            'properties':{'dimension':{'enum':list(DIMS)},'theme':{'type':'string','minLength':1},
                'quote':{'type':'string','minLength':8},'explanation':{'type':'string','minLength':1}}}})
    dump(OUT/'coding_schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema',
        'type':'object','required':list(properties),'properties':properties,
        '$comment':'Custom Python validator additionally checks exact source quotations, unique/dimension-correct IDs, relationship quotes and status consistency. Offline tests exercise research-critical constraints.'})
    log(dict(stage='frozen',sha256=meta['codebook_sha256'],categories=len(cb['categories'])))


def closed_coding(workers,pilot_only):
    units=read(STATE/'evidence_units.json')
    cb=read(OUT/'codebook.json')
    assert sha(OUT/'codebook.json')==read(OUT/'run_manifest.json')['codebook_sha256']
    def process(u):
        user='FROZEN CODEBOOK: '+canonical(cb)+'\nEVIDENCE UNIT: '+canonical(unit_input(u))
        return call('closed',u['evidence_id'],prompt.CODING_SYSTEM,user,
                    lambda r:validate_observation(r,u,cb))
    # Pilot covers two chapters, early/late years and the longest anchor.
    pilots=[]
    for predicate in (lambda u:u['section']=='item7' and u['fiscal_year']==2020,
                      lambda u:u['both_sections_positive'] and u['section']=='item1a',
                      lambda u:u['both_sections_positive'] and u['section']=='item7',
                      lambda u:u['fiscal_year']==2025 and u['section']=='item1a'):
        pilots.append(next(u for u in units if predicate(u)))
    pilots.append(max(units,key=lambda u:len(u['evidence'])))
    for u in pilots:
        s=process(u); log(dict(stage='closed_pilot',id=u['evidence_id'],status=s['status']))
        if s['status']!='complete': raise RuntimeError('Closed coding pilot failed')
    dump(OUT/'closed_coding_pilot_gate.json',dict(passed=True,evidence_ids=[u['evidence_id'] for u in pilots],
        checks=['schema','allowed IDs','exact source quotes','relationship quotes','source hash'],timestamp=now(),
        caveat='Automated integrity validation; not human semantic accuracy'))
    if pilot_only: return
    done=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(process,u):u['evidence_id'] for u in units}
        for future in as_completed(tasks):
            s=future.result(); done+=1
            if done%10==0 or s['status']!='complete': log(dict(stage='closed',done=done,total=len(units),status=s['status'],id=tasks[future]))
    meta=read(OUT/'run_manifest.json'); meta.update(stage='coded',coding_finished_utc=now(),workers=workers)
    dump(OUT/'run_manifest.json',meta)


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    p=argparse.ArgumentParser()
    p.add_argument('--stage',required=True,choices=['prepare','open','supplement','synthesize','freeze','pilot','full','report'])
    p.add_argument('--workers',type=int,default=16)
    args=p.parse_args()
    if args.stage=='prepare': prepare()
    elif args.stage=='open': open_coding(args.workers)
    elif args.stage=='supplement': supplement(args.workers)
    elif args.stage=='synthesize': synthesize()
    elif args.stage=='freeze': freeze()
    elif args.stage in ('pilot','full'): closed_coding(args.workers,args.stage=='pilot')
    elif args.stage=='report':
        from .governance_content_reporting import report
        report()
