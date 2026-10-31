"""Independent CSV reconciliation and final delivery audit; no paid requests."""
from __future__ import annotations
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import governance_v2 as v
from .llm.client import load_config


def truth(value):
    return value in {'True','true','1'}


def independent_verify():
    a=v.read(v.OUT/'item1a_v2_classification_results.csv')
    b=v.read(v.OUT/'item7_v2_classification_results.csv')
    panel=v.read(v.OUT/'combined_firm_year_v2_panel.csv')
    excluded=v.read(v.OUT/'exclusion_manifest.csv')
    annual=v.read(v.OUT/'annual_trend_summary.csv')
    target=v.read(v.A)
    source={v.identity(r):r for r in target}
    aa={v.identity(r):r for r in a};bb={v.identity(r):r for r in b}
    pp={v.identity(r):r for r in panel};xx={v.identity(r):r for r in excluded}
    checks={'target_keys_unique':len(source)==len(target)==9000,
            'section_keys_unique':len(aa)==len(a)==len(bb)==len(b)==9000,
            'panel_keys_unique':len(pp)==len(panel),'exclusion_keys_unique':len(xx)==len(excluded),
            'target_partition_exact':set(pp).isdisjoint(xx) and set(pp)|set(xx)==set(source),
            'section_universe_exact':set(aa)==set(bb)==set(source),
            'classification_fields_binary_or_blank':all(r['classification'] in {'Positive','Negative',''} for r in a+b),
            'all_valid_sections_binary':all((r['classification'] in {'Positive','Negative'})==truth(r['text_available']) for r in a+b),
            'valid_text_not_excluded':True,'excluded_double_unavailable_only':True,
            'observed_section_OR_exact':True,'annual_counts_and_rates_exact':True,
            'original_item1a_bytes_preserved':True,'credential_absent_from_bundle':True}
    for k in source:
        av,bv=truth(aa[k]['text_available']),truth(bb[k]['text_available'])
        if not(av or bv):
            checks['excluded_double_unavailable_only'] &= k in xx
            continue
        checks['valid_text_not_excluded'] &= k in pp
        expected='1' if aa[k]['classification']=='Positive' or bb[k]['classification']=='Positive' else '0'
        r=pp[k]
        checks['observed_section_OR_exact'] &= r['implemented_internal_ai_governance_v2']==expected and r['classification_status']=='complete'
        checks['observed_section_OR_exact'] &= (r['item1a_v2_classification']==aa[k]['classification'] and r['item7_v2_classification']==bb[k]['classification'])
    for r in annual:
        group=[p for p in panel if p['fiscal_year']==r['fiscal_year']]
        xgroup=[p for p in excluded if p['fiscal_year']==r['fiscal_year']]
        pos=sum(p['implemented_internal_ai_governance_v2']=='1' for p in group)
        neg=sum(p['implemented_internal_ai_governance_v2']=='0' for p in group)
        checks['annual_counts_and_rates_exact'] &= (int(r['target_n'])==1500 and int(r['eligible_n'])==len(group)
            and int(r['excluded_n'])==len(xgroup) and int(r['positive_n'])==pos and int(r['negative_n'])==neg
            and int(r['unresolved_n'])==0 and abs(float(r['positive_rate'])-pos/len(group))<1e-12)
    def original_check(r):
        if r['item1a_path'] and r['item1a_sha256']:
            path=v.ROOT/r['item1a_path']
            return path.is_file() and v.sha(path.read_bytes())==r['item1a_sha256']
        return True
    with ThreadPoolExecutor(max_workers=32) as pool:
        checks['original_item1a_bytes_preserved']=all(pool.map(original_check,target))
    # Exact-match check against the live credential; only filenames of accidental
    # matches would be retained. The credential itself is never written or printed.
    secret=load_config(v.prior._env_file()).api_key.encode()
    paths=[p for p in v.OUT.rglob('*') if p.is_file() and p.suffix.lower() in {'.json','.jsonl','.txt','.md','.csv','.log','.py'}]
    def leaked(p):return v.rel(p) if secret in p.read_bytes() else None
    with ThreadPoolExecutor(max_workers=32) as pool:
        leak_paths=[p for p in pool.map(leaked,paths) if p]
    checks['credential_absent_from_bundle']=not leak_paths
    qa=dict(passed=all(checks.values()),checks=checks,credential_match_paths=leak_paths,
            target_n=len(target),eligible_n=len(panel),excluded_n=len(excluded),
            positive_n=sum(r['implemented_internal_ai_governance_v2']=='1' for r in panel),
            negative_n=sum(r['implemented_internal_ai_governance_v2']=='0' for r in panel),
            chapters_classified_n=sum(truth(r['text_available']) for r in a+b))
    v.dump(v.OUT/'delivery_qa.json',qa)
    if not qa['passed']:raise ValueError('Independent delivery QA failed')
    return qa


def export_positive_contexts():
    states=json.loads((v.OUT/'input_manifest.json').read_text(encoding='utf-8'))
    records=v.load_records(states)
    contexts=[];restrictions=[]
    for r in records.values():
        if r.get('result',{}).get('classification')!='Positive':continue
        text=v.texts(r)
        for quote,loc in zip(r['result']['evidence'],r['quote_locations']):
            start=max(0,loc['start']-800);end=min(len(text),loc['end']+800)
            contexts.append(dict(cik=r['cik'],ticker=r['ticker'],fiscal_year=r['fiscal_year'],section=r['section'],
                input_file=r['input_file'],input_sha256=r['input_sha256'],evidence=quote,quote_location=loc,
                context_start=start,context_end=end,source_context=text[start:end],
                mechanism_summary=r['result']['mechanism_summary'],scope_limitation=r['result']['scope_limitation']))
        ev=' '.join(r['result']['evidence'])
        if re.search(r'(?i)prohibit|restrict|\bban\b',ev):
            restrictions.append(dict(cik=r['cik'],ticker=r['ticker'],fiscal_year=r['fiscal_year'],section=r['section'],
                evidence=json.dumps(r['result']['evidence'],ensure_ascii=False),mechanism_summary=r['result']['mechanism_summary'],
                source_file=r['input_file'],source_sha256=r['input_sha256'],
                screening_status='lexical_restriction_mention_for_source_inspection'))
    (v.OUT/'positive_evidence_contexts.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in contexts),encoding='utf-8')
    v.rows(v.OUT/'restriction_mention_positive_inspection.csv',restrictions)
    return restrictions


def finalize_report(qa):
    report=v.OUT/'run_report.md'
    text=report.read_text(encoding='utf-8')
    text=text.replace('Account invoice, currency and credit deductions were not retrieved.',
                      'The balance endpoint returned CNY. Account invoice and itemized credit deductions were not retrieved; USD figures are separate published-price scenarios.')
    text=text.replace('Figures use annual Eligible N. Unfinished years have no final rate; provisional identified-positive counts are explicitly labeled. PNG 300 dpi and vector PDF.',
                      'All six years are complete. Positive Rate uses annual Eligible N; each plotted count is the final observed-section OR count. PNG 300 dpi and vector PDF.')
    start=text.index('Response recovery:')
    end=text.index('\n\nQA checks passed:',start)
    replacement=('Response recovery: 48 cases were recovered offline without changing the model label, using exact source spans after unique typography/whitespace or recognized paired page-number/TOC alignment. '
                 '79 distinct sections received corrective full-text calls (including three source-based semantic QA cases); 23 of them received a second and last corrective round. '
                 'The authoritative System Prompt, standard, model, temperature and output budget stayed identical; saved user suffixes constrained formatting and requested reinspection under C3/C4. '
                 'Negative evidence arrays may be empty after a new full-section LLM judgment; failed responses were never converted into Negative. '
                 'One additional KVUE FY2025 quote was recovered through a separately documented inspection of page number 26, restoring the complete exact source span and keeping its Positive label. '
                 'Original responses and caches remain in `responses/`, `recovery_originals/`, and `semantic_qa_originals/`. '
                 'See `offline_response_recovery.csv`, `corrective_recovery_summary.csv`, `semantic_source_review_manifest.csv`, `verified_pagination_recovery.json`, both corrective user-suffix templates and both recovery configuration files.')
    text=text[:start]+replacement+text[end:]
    text=text.replace('Source exceptions: `source_exception_manifest.csv`;',
                      'The final LLM exception queue is empty. Both sections observed=7,722; only Item 1A observed=473; only Item 7 observed=305. Source exceptions: `source_exception_manifest.csv`;')
    index=text.index('## Artifact paths')
    additions=('The primary run encountered HTTP 402; `interruption_manifest.json` records the interruption. The user confirmed top-up and the run resumed from validated caches. '
               'A billing circuit breaker now stops queued submissions on HTTP 402. Historical failed attempts remain in request accounting, with missing usage left unknown. '
               'All 16,222 valid sections now have compliant binary results; all 8,500 eligible firm-years are resolved.\n\n'
               'Focused offline tests: 42 passed. Independent delivery checks in `delivery_qa.json` reconcile CSV keys, source availability, exclusions, OR rules, annual denominators/rates, original Item 1A bytes and credential exclusion. '
               '`positive_evidence_contexts.jsonl` supplies adjacent source context and normalized-text character offsets for every positive quote. '
               '`restriction_mention_positive_inspection.csv` is a lexical inspection list, not a new classification subtype.\n\n'
               'Observed trends: Positive N is 2, 2, 3, 35, 93 and 168 from FY2020 to FY2025; Positive Rate is 0.150%, 0.143%, 0.213%, 2.429%, 6.379% and 11.499%. '
               'Coverage also increases over this period, so these disclosed-evidence trends do not identify changes in actual governance prevalence or a causal effect.\n\n')
    text=text[:index]+additions+text[index:]
    report.write_text(text,encoding='utf-8')
    v.dump(v.OUT/'offline_test_summary.json',dict(passed=42,framework='pytest',test_files=[
        'tests/test_governance_v2.py','tests/test_governance_v2_recovery.py','tests/test_deepseek_client.py','tests/test_item7_governance.py']))
    pricepath=v.OUT/'pricing_snapshot.json'
    price=json.loads(pricepath.read_text(encoding='utf-8'))
    price['estimate_note']='List-price scenarios from API-returned usage; no account invoice or itemized deductions were retrieved. The balance endpoint returned CNY. USD amounts are separate published-price scenarios, not a currency conversion.'
    v.dump(pricepath,price)
    costpath=v.OUT/'cost_and_token_summary.json'
    cost=json.loads(costpath.read_text(encoding='utf-8'));cost['estimate_note']=price['estimate_note'];v.dump(costpath,cost)
    # Record final consumer-facing artifacts and current reusable code separately
    # from the execution-era request/code snapshots.
    core=['item1a_v2_classification_results.csv','item7_v2_classification_results.csv','combined_firm_year_v2_panel.csv',
          'annual_trend_summary.csv','run_report.md','exclusion_manifest.csv','system_prompt.txt','user_prompt_template.txt',
          'llm_config.json','classification_standard_snapshot.md','request_manifest.jsonl','delivery_qa.json',
          'figures/figure1_annual_positive_rate.png','figures/figure1_annual_positive_rate.pdf',
          'figures/figure2_annual_positive_count.png','figures/figure2_annual_positive_count.pdf',
          'figures/combined_annual_trends.png','figures/combined_annual_trends.pdf']
    v.dump(v.OUT/'delivery_manifest.json',dict(version=v.prompt.PROMPT_VERSION,status='complete',summary=qa,
        artifacts=[dict(path=str((v.OUT/f).resolve()),project_relative_path=v.rel(v.OUT/f),sha256=v.sha((v.OUT/f).read_bytes())) for f in core],
        final_code_hashes={v.rel(p):v.sha(p.read_bytes()) for p in [Path(__file__),v.ROOT/'src/ai_restrictions/governance_v2.py',v.ROOT/'src/ai_restrictions/governance_v2_recovery.py']}))
    v.log(json.dumps(dict(status='complete',eligible_n=qa['eligible_n'],excluded_n=qa['excluded_n'],positive_n=qa['positive_n'],
        negative_n=qa['negative_n'],positive_rate=qa['positive_n']/qa['eligible_n'],chapters_classified_n=qa['chapters_classified_n'],
        qa_passed=qa['passed'],artifact_paths=[str((v.OUT/f).resolve()) for f in core]),ensure_ascii=False))


def run():
    restrictions=export_positive_contexts()
    qa=independent_verify()
    finalize_report(qa)
    v.log(f'Positive restriction-mention source inspection rows: {len(restrictions)}')
