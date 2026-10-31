"""Independent offline delivery checks using CSV/JSON exports and original source."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/implemented_ai_governance_content_analysis'
BASE=ROOT/'outputs/full_universe_implemented_internal_ai_governance_v2'


def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def file_hash(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    binary=rows(BASE/'combined_firm_year_v2_panel.csv')
    assert file_hash(ROOT/'docs/implemented_internal_ai_governance_v2.md')==file_hash(BASE/'classification_standard_snapshot.md')==file_hash(OUT/'binary_standard_snapshot.md')
    expected={(r['cik'],int(r['fiscal_year'])) for r in binary if r['implemented_internal_ai_governance_v2']=='1'}
    panel=rows(OUT/'firm_year_content_panel.csv')
    actual={(r['cik'],int(r['fiscal_year'])) for r in panel}
    assert actual==expected and len(panel)==len(actual)
    cb=json.loads((OUT/'codebook.json').read_text(encoding='utf-8'))
    categories={c['id']:c['dimension'] for c in cb['categories']}
    ev=rows(OUT/'evidence_level_coding.csv')
    assert len({r['evidence_id'] for r in ev})==len(ev)
    original_evidence=sum(len(json.loads(r['evidence'])) for r in rows(BASE/'positive_evidence_audit.csv'))
    assert len(ev)==original_evidence
    source_cache={}; labels=defaultdict(set); item_labels=defaultdict(set); quote_count=0
    for r in ev:
        p=ROOT/r['input_file']
        if str(p) not in source_cache:
            assert file_hash(p)==r['input_sha256']
            source_cache[str(p)]=p.read_text(encoding='utf-8-sig')
        t=source_cache[str(p)]
        assert t[int(r['evidence_start']):int(r['evidence_end'])]==r['evidence']
        if r['coding_status'] not in ('coded','uncodable'): continue
        for dim in ('practices','motivations','visions'):
            for label in json.loads(r[dim]):
                cid=label['category_id']
                assert categories[cid]==dim
                labels[cid].add((r['cik'],int(r['fiscal_year'])))
                item_labels[(cid,r['section'])].add((r['cik'],int(r['fiscal_year'])))
                for loc in label['quote_locations']:
                    assert t[loc['start']:loc['end']]==label['quote']
                quote_count+=1
                if dim!='practices':
                    assert label['explicitness'] in ('Explicit','Implicit')
                    for loc in label['relationship_quote_locations']:
                        assert t[loc['start']:loc['end']]==label['relationship_quote']
    for cid in categories:
        assert {(r['cik'],int(r['fiscal_year'])) for r in panel if r[cid]=='1'}==labels[cid]
    for r in rows(OUT/'category_statistics.csv'):
        cid=r['category_id']
        if r['scope']=='all':
            assert int(r['firm_year_count'])==len(labels[cid])
            assert int(r['denominator'])==len(expected)
            assert abs(float(r['percentage'])-100*len(labels[cid])/len(expected))<1e-9
        if r['dimension']!='practices':
            assert int(r['explicit_count'])+int(r['implicit_only_count'])==int(r['firm_year_count'])
    queue=rows(OUT/'review_queue.csv')
    assert all(not r['human_decision'] and r['status']=='pending_human_review' for r in queue)
    assert len({r['record_id'] for r in queue})==len(queue)
    item_keys={item:{(r['cik'],int(r['fiscal_year'])) for r in ev if r['section']==item} for item in ('item1a','item7')}
    figure_data=rows(OUT/'figure_data.csv')
    for r in figure_data:
        fig=r['figure']; cid=r['category']; den=len(panel)
        if fig.startswith(('01','02','03')):
            if cid in categories: count=len(labels[cid])
            else:
                dim='motivations' if fig.startswith('02') else 'visions'
                wanted=['Not Disclosed'] if cid=='Not Disclosed' else ['Uncertain','Observed_with_uncertainty']
                count=sum(p[dim+'_disclosure_status'] in wanted for p in panel)
        elif fig.startswith('04'):
            ps=[p for p in panel if p['fiscal_year']==r['fiscal_year']]
            den=len(ps); count=sum(p[cid]=='1' for p in ps)
        elif fig.startswith('05'):
            count=sum(p[cid]=='1' and p[r['category_2']]=='1' for p in panel)
        elif fig.startswith('06'):
            count=sum(p[cid]=='1' and p[r['category_2']+'_explicit']=='1' for p in panel)
        else:
            item=r['source_item']; den=len(item_keys[item]); count=len(item_labels[(cid,item)])
        assert int(r['count'])==count and int(r['denominator'])==den
        if r.get('percentage'): assert abs(float(r['percentage'])-100*count/den)<1e-9
    positioning=rows(OUT/'governance_positioning_summary.csv')
    risk={(p['cik'],p['fiscal_year']) for p in panel if any(p[c+'_explicit']=='1' for c in ['V02','V03','V04','V06','V08','V09'])}
    adoption={(p['cik'],p['fiscal_year']) for p in panel if p['V05_explicit']=='1'}
    assert [int(r['count']) for r in positioning]==[len(risk),len(adoption),len(risk&adoption),len(panel)-len(risk|adoption)]
    manifest=json.loads((OUT/'delivery_manifest.json').read_text(encoding='utf-8'))
    bad=[name for name,h in manifest['files'].items() if file_hash(OUT/name)!=h]
    assert not bad,bad
    assert len(list((OUT/'figures').glob('*.png')))==7
    result=dict(passed=True,positive_firm_years=len(expected),evidence_rows=len(ev),
        labels_checked=quote_count,source_files_hash_checked=len(source_cache),
        category_set_union_reconciled=len(categories),queue_rows=len(queue),
        figure_source_rows_checked=len(figure_data),positioning_groups_checked=len(positioning),
        final_figure_count=7,human_decisions_created=0,
        caveat='Independent implementation of integrity checks, not independent human semantic validation.')
    (OUT/'independent_qa.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    manifest['files']['independent_qa.json']=file_hash(OUT/'independent_qa.json')
    (OUT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__': main()
