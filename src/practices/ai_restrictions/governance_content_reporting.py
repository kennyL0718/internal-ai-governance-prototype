"""Auditable firm-year aggregation, tables, review aids, and Matplotlib figures."""
from __future__ import annotations

import importlib.util
import itertools
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from . import governance_content as g


def aggregate(units, coded, cb):
    """Set union by CIK/fiscal year; no model-generated panel or double counting."""
    groups=defaultdict(list)
    for u in units: groups[(u['cik'],u['fiscal_year'])].append(u)
    cats=cb['categories']
    panel=[]
    for (cik,year),us in sorted(groups.items()):
        valid=[coded[u['evidence_id']] for u in us if u['evidence_id'] in coded]
        failed=len(us)-len(valid)
        r=dict(cik=cik,ticker=us[0]['ticker'],company_name=us[0]['company_name'],
            fiscal_year=year,sector=us[0]['sector'],positive_binary_v2=1,
            evidence_n=len(us),coded_evidence_n=len(valid),failed_evidence_n=failed,
            uncodable_evidence_n=sum(x['uncodable'] for x in valid),
            flagged_evidence_n=sum(x['review_flag'] for x in valid),
            emerging_evidence_n=sum(bool(x['emerging_themes']) for x in valid),
            source_items=sorted({u['section'] for u in us}),
            coding_status='incomplete' if failed else ('complete_with_review' if any(x['review_flag'] for x in valid) else 'complete'),
            human_review_status='not_reviewed')
        for dim in g.DIMS:
            r[dim+'_categories']=sorted({v['category_id'] for x in valid for v in x[dim]})
            if dim!='practices':
                statuskey='motivation_status' if dim=='motivations' else 'vision_status'
                types={v['explicitness'] for x in valid for v in x[dim]}
                uncertain=(failed or any(x[statuskey]=='Uncertain' or x['uncodable'] for x in valid)
                    or any(e['dimension']==dim for x in valid for e in x['emerging_themes']))
                # Separate existence of supported labels from completeness of absence.
                r[dim+'_disclosure_status']=('Observed_with_uncertainty' if types and uncertain else
                    ('Uncertain' if uncertain else ('Mixed' if len(types)>1 else
                    (next(iter(types)) if types else 'Not Disclosed'))))
                r[dim+'_explicit_categories']=sorted({v['category_id'] for x in valid for v in x[dim] if v['explicitness']=='Explicit'})
                r[dim+'_implicit_categories']=sorted({v['category_id'] for x in valid for v in x[dim] if v['explicitness']=='Implicit'})
        for c in cats:
            vals=[v for x in valid for v in x[c['dimension']] if v['category_id']==c['id']]
            r[c['id']]=int(bool(vals))
            if c['dimension']!='practices':
                r[c['id']+'_explicit']=int(any(v['explicitness']=='Explicit' for v in vals))
                r[c['id']+'_implicit_any']=int(any(v['explicitness']=='Implicit' for v in vals))
                r[c['id']+'_implicit_only']=int(bool(vals) and not r[c['id']+'_explicit'])
        panel.append(r)
    return panel


def statistics(units,coded,cb,panel):
    cats=cb['categories']; n=len(panel)
    stats=[]
    for c in cats:
        cid=c['id']; dim=c['dimension']
        for scope,value,ps in [('all','all',panel)]+[
            ('fiscal_year',year,[r for r in panel if r['fiscal_year']==year]) for year in range(2020,2026)]:
            den=len(ps); count=sum(r[cid] for r in ps)
            ex=sum(r.get(cid+'_explicit',0) for r in ps)
            im=sum(r.get(cid+'_implicit_only',0) for r in ps)
            stats.append(dict(dimension=dim,category_id=cid,category_name=c['name'],scope=scope,scope_value=value,
                firm_year_count=count,denominator=den,percentage=100*count/den if den else '',
                unique_company_count=len({r['cik'] for r in ps if r[cid]}),
                explicit_count=ex if dim!='practices' else '',implicit_only_count=im if dim!='practices' else '',
                raw_implicit_any_count=sum(r.get(cid+'_implicit_any',0) for r in ps) if dim!='practices' else '',
                explicit_percentage=100*ex/den if dim!='practices' and den else '',
                multi_label=True,denominator_definition='all original Positive firm-years in scope, including incomplete/review cases'))
        for item in ('item1a','item7'):
            eligible={(u['cik'],u['fiscal_year']) for u in units if u['section']==item}
            hits={(u['cik'],u['fiscal_year']) for u in units if u['section']==item and
                  any(v['category_id']==cid for v in coded.get(u['evidence_id'],{}).get(dim,[]))}
            ex={(u['cik'],u['fiscal_year']) for u in units if u['section']==item and
                  any(v['category_id']==cid and v.get('explicitness')=='Explicit' for v in coded.get(u['evidence_id'],{}).get(dim,[]))}
            stats.append(dict(dimension=dim,category_id=cid,category_name=c['name'],scope='source_item',scope_value=item,
                firm_year_count=len(hits),denominator=len(eligible),percentage=100*len(hits)/len(eligible),
                unique_company_count=len({k[0] for k in hits}),
                explicit_count=len(ex) if dim!='practices' else '',implicit_only_count=len(hits-ex) if dim!='practices' else '',
                all_positive_denominator=n,percentage_all_positive=100*len(hits)/n,multi_label=True,
                denominator_definition='Positive firm-years in this source chapter; within-firm/category deduplicated'))
    # Dimension-level absent/uncertain counts must not vanish inside category tables.
    status=[]
    for dim in ('motivations','visions'):
        for scope,value,ps in [('all','all',panel)]+[
            ('fiscal_year',year,[r for r in panel if r['fiscal_year']==year]) for year in range(2020,2026)]:
            for label in ('Explicit','Implicit','Mixed','Not Disclosed','Uncertain','Observed_with_uncertainty'):
                count=sum(r[dim+'_disclosure_status']==label for r in ps)
                status.append(dict(dimension=dim,status=label,scope=scope,scope_value=value,count=count,
                    denominator=len(ps),percentage=100*count/len(ps)))
    g.csvout(g.OUT/'category_statistics.csv',stats)
    g.csvout(g.OUT/'disclosure_status_statistics.csv',status)
    # Same-firm/year co-disclosure, no claim that practices cause motives.
    pairs=[]
    bydim={d:[c for c in cats if c['dimension']==d] for d in g.DIMS}
    for a,b in (('practices','practices'),('practices','motivations'),('motivations','visions')):
        for c1 in bydim[a]:
            for c2 in bydim[b]:
                k1=c1['id']; k2=c2['id']; k2x=k2 if b=='practices' else k2+'_explicit'
                k1x=k1 if a=='practices' else k1+'_explicit'
                count=sum(r[k1x] and r[k2x] for r in panel)
                n1=sum(r[k1x] for r in panel); n2=sum(r[k2x] for r in panel)
                pairs.append(dict(dimension_1=a,dimension_2=b,category_1=k1,category_2=k2,
                    count=count,all_positive_denominator=n,percentage_all_positive=100*count/n,
                    row_category_denominator=n1,row_conditional_percentage=100*count/n1 if n1 else '',
                    jaccard=count/(n1+n2-count) if n1+n2-count else 0,
                    evidence_policy='explicit-only motives and visions; same firm-year co-disclosure, not a verified direct pair linkage'))
    g.csvout(g.OUT/'cross_dimension_statistics.csv',pairs)
    sensitivity=[]
    for c in cats:
        clean_hits={(u['cik'],u['fiscal_year']) for u in units if u['evidence_id'] in coded and
            not coded[u['evidence_id']]['review_flag'] and not coded[u['evidence_id']]['uncodable'] and
            any(v['category_id']==c['id'] for v in coded[u['evidence_id']][c['dimension']])}
        sensitivity.append(dict(category_id=c['id'],category_name=c['name'],dimension=c['dimension'],
            all_validated_model_label_count=sum(r[c['id']] for r in panel),
            count_supported_by_unflagged_evidence=len(clean_hits),denominator=n,
            unflagged_percentage_all_positive=100*len(clean_hits)/n,
            caveat='Automated review flags only; unflagged does not mean human-verified'))
    g.csvout(g.OUT/'review_flag_sensitivity.csv',sensitivity)
    return stats,status,pairs


def review_queue(units,coded,cb):
    rng=random.Random(20261018)
    firmkeys=sorted({(u['cik'],u['fiscal_year']) for u in units})
    sample=set(rng.sample(firmkeys,min(30,len(firmkeys))))
    boundary=[u['evidence_id'] for u in units if u['evidence_id'] in coded and
        any(v.get('explicitness')=='Implicit' for d in ('motivations','visions') for v in coded[u['evidence_id']][d])]
    boundary=set(rng.sample(boundary,min(20,len(boundary))))
    pilot_ids=set(g.read(g.OUT/'closed_coding_pilot_gate.json')['evidence_ids'])
    queue=[]
    for u in units:
        x=coded.get(u['evidence_id'])
        why=[]
        if not x: why.append('coding_failure')
        elif x['review_flag'] or x['uncodable'] or x['emerging_themes']: why.append('model_flag: '+x['review_reason'])
        if (u['cik'],u['fiscal_year']) in sample: why.append('random_firm_year_QA_seed_20261018')
        if u['evidence_id'] in boundary: why.append('implicit_link_boundary_sample')
        if u['evidence_id'] in pilot_ids: why.append('closed_coding_pilot_QA')
        if not why: continue
        labels={d:[v['category_id'] for v in x[d]] if x else [] for d in g.DIMS}
        queue.append(dict(record_id=u['evidence_id'],cik=u['cik'],ticker=u['ticker'],company_name=u['company_name'],
            fiscal_year=u['fiscal_year'],source_item=u['section'],source_path=u['input_file'],
            source_sha256=u['input_sha256'],evidence_start=u['evidence_start'],evidence_end=u['evidence_end'],
            evidence=u['evidence'],source_context=u['source_context'],model_label=labels,
            companion_context_blocks=u.get('context_blocks',[]),
            model_reason=g.canonical(x) if x else 'coding failed; unresolved',
            review_reason='; '.join(why),status='pending_human_review',
            human_decision='',human_practice_categories='',human_motivation_categories='',
            human_vision_categories='',human_quote_correction='',human_notes='',reviewer='',reviewed_at=''))
    target=g.STATE/'review_queue.csv'
    g.csvout(target,queue)
    shutil.copyfile(target,g.OUT/'review_queue.csv')
    cfg=dict(project_root=str(g.ROOT),queue_path=target.relative_to(g.ROOT).as_posix(),
        database_path='data/interim/human_review/governance_content_reviews.sqlite3',
        field_map=dict(identity='record_id',source_hash='source_sha256',text_path='source_path',
            company='company_name',year='fiscal_year',model_label='model_label',model_reason='model_reason',
            evidence='evidence',status='status'),
        decisions=['主题和证据可以接受','修改实践标签','修改动机标签或显隐程度','修改目标标签或显隐程度','引用或上下文问题','无法编码','暂时无法判断'])
    g.dump(g.ROOT/'config/human_review_governance_content.json',cfg)
    # Read-only integration check: use existing queue parser, do not write decisions/DB.
    shared=Path('C:/Users/62638/Desktop/workflow/human-review/review_core.py')
    integration=dict(shared_program_available=shared.exists(),queue_rows=len(queue),random_firm_years=len(sample),
        implicit_boundary_evidence=len(boundary),database_created=False,human_decisions_created=0)
    if shared.exists():
        spec=importlib.util.spec_from_file_location('content_shared_review',shared)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        loaded,_=mod.load_queue(target,field_map=cfg['field_map'],project_root=g.ROOT)
        assert len(loaded)==len(queue)
        integration['shared_parser_loaded_rows']=len(loaded)
        integration['unique_review_ids']=len({r['review_id'] for r in loaded})
    g.dump(g.OUT/'human_review_integration_qa.json',integration)
    (g.OUT/'human_review_instructions.md').write_text('''# 人工复核

复用共享 human-review Streamlit 程序，没有另建界面。配置：
`config/human_review_governance_content.json`。正式队列位于 data/interim；
本目录 review_queue.csv 为交付快照。数据库单独设置为
`data/interim/human_review/governance_content_reviews.sqlite3`，本次未建立或写入人工决定。

队列包括所有模型标记/不可编码/失败，以及 seed=20261018 随机抽取的 30 个 firm-year
的全部 Evidence，另抽最多 20 条隐式关系边界 Evidence。随机样本与边界样本须分别评估。
review_reason 标明入选原因；不能用这个混合队列直接计算全样本错误率。

启动示例（共享技能的现有运行环境）：
```powershell
$env:HUMAN_REVIEW_CONFIG = (Resolve-Path 'config/human_review_governance_content.json').Path
$env:PYTHONPATH = 'C:/Users/62638/Desktop/workflow/human-review/.deps'
& 'C:/Users/62638/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m streamlit run 'C:/Users/62638/Desktop/workflow/human-review/app.py' --global.developmentMode false --server.address 127.0.0.1 --browser.gatherUsageStats false
```

先验证原文及类别引文，随后逐维度审核定义、动机/目标关联、显式/隐式和未来/当前边界。
共享工具保存明确人工提交，标签细节和修订原因记入备注；CSV 也保留各维度修订字段。
人工审核尚未开展；LLM 自洽性、引用匹配和自动 QA 均不能替代人工分类准确率。
''',encoding='utf-8')
    return queue,integration


def examples(units,coded,cb):
    byid={u['evidence_id']:u for u in units}
    lines=['# Representative Disclosure Examples','',
        '下列为可追溯的模型编码示例，优先选择无模型 review flag 的证据；未冒充独立人工验证。',
        '每个类别最多选取 3 个不同公司；数量不足时保留真实可用数量。','']
    chosen={}
    for c in cb['categories']:
        candidates=[]
        for eid,x in coded.items():
            for v in x[c['dimension']]:
                if v['category_id']==c['id']:
                    q=v['quote']
                    coherence_penalty=abs(len(q)-260)+(200 if len(q)<65 else 0)+(60 if not q.rstrip().endswith(('.', ';')) else 0)
                    candidates.append((x['review_flag'],v.get('explicitness')=='Implicit',coherence_penalty,eid,v))
        candidates.sort()
        selections=[]; firms=set()
        for _,_,_,eid,v in candidates:
            u=byid[eid]
            if u['cik'] in firms: continue
            selections.append((u,v,coded[eid])); firms.add(u['cik'])
            if len(selections)==3: break
        chosen[c['id']]=selections
        lines += [f"## {c['id']} {c['name']}（{c['name_zh']}）",'']
        for u,v,x in selections:
            lines += [f"### {u['company_name']} ({u['ticker']}) FY{u['fiscal_year']} {u['section']}",'',
                f"Evidence ID: `{u['evidence_id']}`；原文 `{u['input_file']}`；引用位置 {v['quote_locations']}。",'',
                '> '+v['quote'].replace('\n','\n> '),'',
                f"Explanation: {v['explanation']}；explicitness={v.get('explicitness','implemented practice')}；review={x['review_flag']}。",'']
            if v.get('relationship_quote') and v['relationship_quote']!=v['quote']:
                lines += ['Governance relationship quote:','',
                    '> '+v['relationship_quote'].replace('\n','\n> '),'']
    special=[]
    # Selection terms identify categories after induction, never preassign labels.
    searches=[('风险缓释案例','motivations',('risk','mitigat')),
              ('Responsible / Ethical AI 案例','visions',('responsib','ethic')),
              ('治理与 Adoption / Business Value / Innovation 的关联案例','visions',('adoption','innovation','enable','value'))]
    for title,dim,terms in searches:
        options=[c for c in cb['categories'] if c['dimension']==dim and any(t in (c['name']+' '+c['definition']).lower() for t in terms)]
        if title=='风险缓释案例': options.sort(key=lambda c:c['id']!='M08')
        found=None
        for c in options:
            matches=[x for x in chosen[c['id']] if x[1].get('explicitness')=='Explicit' and not x[2]['review_flag']]
            if matches: found=(c,matches[0]); break
        lines += [f'## {title}','']
        if not found: lines += ['没有足够的显式、无模型复核标记案例；不强行归类。','']
        else:
            c,(u,v,x)=found
            lines += [f"{u['company_name']} ({u['ticker']}) FY{u['fiscal_year']} {u['section']}，{c['id']}，`{u['evidence_id']}`。",'',
                      '> '+v['quote'].replace('\n','\n> '),'',v['explanation'],'']
            if v.get('relationship_quote') and v['relationship_quote']!=v['quote']:
                lines += ['Governance relationship quote:','',
                    '> '+v['relationship_quote'].replace('\n','\n> '),'']
            special.append(dict(type=title,category_id=c['id'],evidence_id=u['evidence_id'],quote=v['quote'],
                company_name=u['company_name'],ticker=u['ticker'],fiscal_year=u['fiscal_year'],source_item=u['section'],
                source_path=u['input_file'],quote_locations=v['quote_locations'],relationship_quote=v.get('relationship_quote',''),
                explanation=v['explanation']))
    firm_units=defaultdict(list)
    for u in units: firm_units[(u['cik'],u['fiscal_year'])].append(u)
    nd_firms={k for k,us in firm_units.items() if all(u['evidence_id'] in coded and
        coded[u['evidence_id']]['motivation_status']=='Not Disclosed' and coded[u['evidence_id']]['vision_status']=='Not Disclosed'
        and not coded[u['evidence_id']]['review_flag'] and not coded[u['evidence_id']]['uncodable'] for u in us)}
    nod=[(byid[eid],x) for eid,x in coded.items() if x['practices']
         and (byid[eid]['cik'],byid[eid]['fiscal_year']) in nd_firms]
    lines += ['## 有明确实践、但该 firm-year 分析文本未披露动机或目标','']
    if nod:
        u,x=min(nod,key=lambda z:len(z[0]['evidence']))
        q=max(x['practices'],key=lambda v:len(v['quote']))['quote']
        lines += [f"{u['company_name']} ({u['ticker']}) FY{u['fiscal_year']} {u['section']}，`{u['evidence_id']}`。",'',
            '> '+q.replace('\n','\n> '),'',
            '实践标签：'+', '.join(v['category_id'] for v in x['practices'])+'；该 firm-year 全部分析证据及上下文均未披露动机与目标。','']
        special.append(dict(type='practice_without_disclosed_motive_or_vision',evidence_id=u['evidence_id'],quote=q,
            company_name=u['company_name'],ticker=u['ticker'],fiscal_year=u['fiscal_year'],source_item=u['section'],
            source_path=u['input_file'],quote_locations=g.exact_quote(q,u),
            category_id=', '.join(v['category_id'] for v in x['practices']),
            explanation='Implemented practice observed; motives and visions Not Disclosed across all analyzed evidence for this firm-year.'))
    else: lines += ['没有满足条件的无复核标记案例。','']
    g.dump(g.OUT/'special_examples.json',special)
    (g.OUT/'representative_examples.md').write_text('\n'.join(lines),encoding='utf-8')


def figures(cb,panel,stats,status,pairs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import textwrap
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':14,
        'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,
        'svg.fonttype':'none','figure.facecolor':'white','savefig.facecolor':'white'})
    out=g.OUT/'figures'; out.mkdir(exist_ok=True)
    n=len(panel); colors=['#285A7C','#A9C9D9','#C3C6CB']
    short={
        'P01':'Policies and frameworks','P02':'AI governance bodies and committees',
        'P03':'Review and approval gates','P04':'Testing, validation and risk assessment',
        'P05':'AI/ML model risk management','P06':'Permissible use and vendor restrictions',
        'P07':'Technical access and data controls','P08':'Workforce training and awareness',
        'P09':'Monitoring, enforcement and reporting','P10':'Human and expert oversight',
        'P11':'Operational pause and incident review','P12':'Regulatory monitoring and adaptation',
        'M01':'Legal and regulatory compliance','M02':'Data, confidentiality and IP protection',
        'M03':'Cybersecurity and technical security','M04':'Model and output performance risk',
        'M05':'Responsible, ethical and trustworthy AI','M06':'Unauthorized or noncompliant AI use',
        'M07':'Reputation and public trust','M08':'General AI risk mitigation',
        'M09':'AI opportunities and business value','V01':'Responsible, ethical and safe AI use',
        'V02':'Reliable model and output performance','V03':'Data, systems and IP protection',
        'V04':'External legal and standards compliance','V05':'AI adoption, innovation and value',
        'V06':'Internal policy adherence','V07':'Explainability and expert validation',
        'V08':'Public trust and reputation','V09':'General AI risk reduction'}
    g.csvout(g.OUT/'figure_label_dictionary.csv',[dict(category_id=c['id'],full_name=c['name'],
        figure_label=short.get(c['id'],c['name'])) for c in cb['categories']])
    bydim={d:sorted([c for c in cb['categories'] if c['dimension']==d],
                key=lambda c:-sum(r[c['id']] for r in panel)) for d in g.DIMS}
    sources=[]
    def save(fig,name,note):
        fig.text(.015,.012,note,fontsize=8,color='#444444',va='bottom',wrap=True)
        for ext in ('png','pdf','svg'): fig.savefig(out/(name+'.'+ext),dpi=300,bbox_inches='tight')
        plt.close(fig)
    def labels(cs): return ['\n'.join(textwrap.wrap(short.get(c['id'],c['name']),37)) for c in cs]
    for dim,name,title in [('practices','01_practices_frequency','Disclosed governance practices'),
                           ('motivations','02_motivations_distribution','Disclosed governance motivations'),
                           ('visions','03_visions_distribution','Disclosed governance objectives and vision')]:
        cs=bydim[dim]
        extra=0 if dim=='practices' else 2
        fig,ax=plt.subplots(figsize=(11,max(5.4,len(cs)*.58+2)),layout='constrained')
        fig.get_layout_engine().set(rect=(0,.10,1,.90))
        ys=np.arange(len(cs)+extra)
        values=[sum(r[c['id']] for r in panel) for c in cs]
        labs=labels(cs)
        if dim=='practices':
            ax.barh(ys,values,color=colors[0],height=.65)
        else:
            ex=[sum(r[c['id']+'_explicit'] for r in panel) for c in cs]
            im=[sum(r[c['id']+'_implicit_only'] for r in panel) for c in cs]
            nd=sum(r[dim+'_disclosure_status']=='Not Disclosed' for r in panel)
            un=sum(r[dim+'_disclosure_status'] in ('Uncertain','Observed_with_uncertainty') for r in panel)
            labs+=['Not disclosed in evidence/context','Uncertain or observed with uncertainty']
            ex += [0,0]; im += [0,0]; values += [nd,un]
            ax.barh(ys,ex,color=colors[0],height=.65,label='Explicit')
            ax.barh(ys,im,left=ex,color=colors[1],height=.65,label='Implicit only')
            ax.barh(ys[-2:],[nd,un],color=colors[2],height=.65,label='Dimension-level status')
            ax.legend(loc='lower right',frameon=False,fontsize=9)
        for y,v in zip(ys,values): ax.text(v+max(values+[1])*.018,y,f'{v}  ({100*v/n:.1f}%)',va='center',fontsize=9)
        ax.set(yticks=ys,yticklabels=labs,xlim=(0,max(values+[1])*1.34),xlabel='Positive firm-years',title=title)
        ax.invert_yaxis(); ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True)
        save(fig,name,f'N = {n} original Positive firm-years. Multi-label; each category counted once per firm-year.\n'
            +('Motives/goals: Explicit takes precedence within category. Gray rows are dimension-level statuses.\n' if dim!='practices' else '')
            +'Validated LLM labels; human review pending. Disclosure frequency does not measure governance effectiveness.')
        for c,v in zip(cs,values): sources.append(dict(figure=name,category=c['id'],count=v,denominator=n,
            explicit_count=sum(r.get(c['id']+'_explicit',0) for r in panel) if dim!='practices' else '',
            implicit_only_count=sum(r.get(c['id']+'_implicit_only',0) for r in panel) if dim!='practices' else ''))
        if dim!='practices':
            sources += [dict(figure=name,category='Not Disclosed',count=nd,denominator=n),
                        dict(figure=name,category='Uncertain or observed with uncertainty',count=un,denominator=n)]
    def heat(matrix,cs1,cs2,title,name,note,fmt='.0f',cbar='Firm-years',maxval=None):
        fig,ax=plt.subplots(figsize=(max(8,len(cs2)*.65+4),max(6,len(cs1)*.5+3)),layout='constrained')
        fig.get_layout_engine().set(rect=(0,.13,1,.87))
        im=ax.imshow(matrix,cmap='Blues',aspect='auto',vmin=0,vmax=maxval)
        ylabels=[c['id']+'  '+label for c,label in zip(cs1,labels(cs1))]
        xlabels=[c['id'] if isinstance(c,dict) else str(c) for c in cs2]
        ax.set(yticks=range(len(cs1)),yticklabels=ylabels,xticks=range(len(cs2)),xticklabels=xlabels,title=title)
        for i in range(len(cs1)):
            for j in range(len(cs2)):
                val=matrix[i,j]; ax.text(j,i,format(val,fmt),ha='center',va='center',fontsize=8,
                    color='white' if val>(maxval or matrix.max() or 1)*.57 else '#222222')
        fig.colorbar(im,ax=ax,shrink=.75,label=cbar)
        save(fig,name,note)
    cs=bydim['practices']; years=list(range(2020,2026))
    annual=[sum(r['fiscal_year']==y for r in panel) for y in years]
    matrix=np.array([[100*sum(r[c['id']] for r in panel if r['fiscal_year']==y)/den
                      for y,den in zip(years,annual)] for c in cs])
    sources += [dict(figure='04_practices_by_year',category=c['id'],fiscal_year=y,
        count=sum(r[c['id']] for r in panel if r['fiscal_year']==y),denominator=den,
        percentage=matrix[i,j]) for i,c in enumerate(cs) for j,(y,den) in enumerate(zip(years,annual))]
    heat(matrix,cs,[f'{y}\nN={den}' for y,den in zip(years,annual)],
        'Practice themes within annual Positive samples','04_practices_by_year',
        'Cells: % of original Positive firm-years within each fiscal year; multi-label.\n'
        'FY2020-2022 have only 2, 2 and 3 firm-years. Changes also reflect company composition and disclosure context.',fmt='.1f',cbar='Annual Positive firm-years (%)',maxval=100)
    co=np.array([[sum(r[c1['id']] and r[c2['id']] for r in panel) for c2 in cs] for c1 in cs])
    sources += [dict(figure='05_practices_cooccurrence',category=c1['id'],category_2=c2['id'],
        count=int(co[i,j]),denominator=n) for i,c1 in enumerate(cs) for j,c2 in enumerate(cs)]
    heat(co,cs,cs,'Practice co-disclosure in the same firm-year','05_practices_cooccurrence',
        f'N = {n} Positive firm-years. Counts deduplicated within firm-year; diagonal = category frequency.\n'
        +'Columns use category IDs. Full ID definitions and count/Jaccard tables accompany the figures.')
    ms=bydim['motivations']
    cross=np.array([[sum(r[c['id']] and r[m['id']+'_explicit'] for r in panel) for m in ms] for c in cs])
    sources += [dict(figure='06_practices_motivations',category=c['id'],category_2=m['id'],
        count=int(cross[i,j]),denominator=n,explicitness='Explicit') for i,c in enumerate(cs) for j,m in enumerate(ms)]
    heat(cross,cs,ms,'Practices and explicitly disclosed motivations','06_practices_motivations',
        f'N = {n} Positive firm-years. Cells count same-firm-year co-disclosure; motives require explicit evidence.\n'
        +'Co-disclosure does not establish a direct linkage between every practice and motive. Columns use codebook IDs.')
    fig,ax=plt.subplots(figsize=(11,max(5.8,len(cs)*.6+2)),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.12,1,.88))
    ys=np.arange(len(cs)); chapter_stats={(r['category_id'],r['scope_value']):r for r in stats if r['scope']=='source_item'}
    for off,item,col in [(-.19,'item1a',colors[0]),(.19,'item7',colors[1])]:
        vals=[chapter_stats[(c['id'],item)]['percentage'] for c in cs]
        den=chapter_stats[(cs[0]['id'],item)]['denominator']
        sources += [dict(figure='07_item_topic_distribution',category=c['id'],source_item=item,
            count=chapter_stats[(c['id'],item)]['firm_year_count'],denominator=den,
            percentage=chapter_stats[(c['id'],item)]['percentage']) for c in cs]
        ax.barh(ys+off,vals,height=.34,color=col,label=f'{"Item 1A" if item=="item1a" else "Item 7"} (N={den})')
        for y,c,v in zip(ys,cs,vals):
            ax.text(v+.7,y+off,f"{chapter_stats[(c['id'],item)]['firm_year_count']}",fontsize=8,va='center')
    ax.set(yticks=ys,yticklabels=labels(cs),xlabel='Share within chapter-specific Positive firm-years (%)',
           title='Practice themes by disclosure chapter',xlim=(0,110))
    ax.invert_yaxis(); ax.legend(frameon=False,loc='lower right'); ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True)
    save(fig,'07_item_topic_distribution','Denominator differs by chapter; label = firm-year count. Multi-label, within-chapter deduplication.\n'
         +'Three firm-years are Positive in both chapters. Chapter selection and company composition limit comparisons.')
    g.csvout(g.OUT/'figure_data.csv',sources)


def accounting():
    events=[]
    p=g.STATE/'request_manifest.jsonl'
    if p.exists(): events=[json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
    received=[e for e in events if e['status']=='response_received']
    usage=Counter()
    for e in received: usage.update({k:v for k,v in e.get('token_usage',{}).items() if type(v) is int})
    rates=g.read(g.OUT/'pricing_snapshot.json') if (g.OUT/'pricing_snapshot.json').exists() else None
    keys=('prompt_cache_hit_tokens','prompt_cache_miss_tokens','completion_tokens')
    incomplete=sum(any(type(e.get('token_usage',{}).get(k)) is not int for k in keys) for e in received)
    cost=None
    if rates and not incomplete:
        cost={period:sum(usage[k]*rates['USD'][period][k]/1e6 for k in keys) for period in ('off_peak','peak')}
    result=dict(api_attempts=sum(e['status']=='started' for e in events),received_responses=len(received),
        logical_requests=len(list((g.STATE/'requests').glob('*/*.json'))),
        by_stage=dict(Counter(e['stage'] for e in events if e['status']=='started')),
        usage=dict(usage),returned_models=dict(Counter(e.get('returned_model','') for e in received)),
        reasoning_tokens=sum(e.get('token_usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for e in received),
        attempts_without_usage_response=sum(e['status']=='started' for e in events)-len(received),
        http_error_attempts=sum(e['status']=='failure' and e.get('error','').startswith('HTTP ') for e in events),
        response_usage_incomplete_n=incomplete,actual_account_cost=None,
        USD_published_price_scenarios=cost,
        cost_note='Provider-returned token usage, including received retries. Attempts without usage include HTTP rejections, network failures, and an interrupted request. List-price scenarios are not an account invoice. Sunday is off-peak under dated official schedule.',
        earliest_event_utc=min((e['time_utc'] for e in events),default=None),latest_event_utc=max((e['time_utc'] for e in events),default=None))
    if result['earliest_event_utc']:
        from datetime import datetime
        result['wall_clock_seconds']=(datetime.fromisoformat(result['latest_event_utc'])-datetime.fromisoformat(result['earliest_event_utc'])).total_seconds()
    g.dump(g.OUT/'cost_and_token_summary.json',result)
    return result


def report():
    units=g.read(g.STATE/'evidence_units.json'); cb=g.read(g.OUT/'codebook.json')
    assert g.sha(g.OUT/'codebook.json')==g.read(g.OUT/'run_manifest.json')['codebook_sha256']
    coded={}; failures=[]; evidence_rows=[]; assigned=[]
    for u in units:
        p=g.STATE/'cache/closed'/(u['evidence_id']+'.json')
        cache=g.read(p) if p.exists() else dict(status='not_submitted')
        base={k:v for k,v in u.items() if k!='source_context'}
        if cache['status']!='complete':
            failures.append(dict(evidence_id=u['evidence_id'],status=cache['status'],errors=cache.get('errors',[])))
            evidence_rows.append(dict(**base,coding_status=cache['status'],review_flag=True,error=cache.get('errors',[])))
            continue
        x=cache['result']; g.validate_observation(x,u,cb)
        user='FROZEN CODEBOOK: '+g.canonical(cb)+'\nEVIDENCE UNIT: '+g.canonical(g.unit_input(u))
        expected_payload=g.build_payload(g.prompt.CODING_SYSTEM,user,max_tokens=16384)
        assert cache['payload_sha256']==g.digest(g.canonical(expected_payload).encode()), 'Stale closed-coding cache'
        # Work on a copy: preserve model cache verbatim.
        x=json.loads(json.dumps(x))
        for dim in g.DIMS:
            for v in x[dim]:
                v['quote_locations']=g.exact_quote(v['quote'],u)
                if dim!='practices': v['relationship_quote_locations']=g.exact_quote(v['relationship_quote'],u)
                assigned.append(dict(v,evidence_id=u['evidence_id'],cik=u['cik'],ticker=u['ticker'],fiscal_year=u['fiscal_year'],
                    section=u['section'],dimension=dim))
        coded[u['evidence_id']]=x
        evidence_rows.append({**base,**x,'coding_status':'uncodable' if x['uncodable'] else 'coded',
            'motivation_explicitness':x['motivation_status'],'vision_explicitness':x['vision_status'],
            'returned_model':cache['metadata'].get('returned_model',''),'codebook_sha256':g.sha(g.OUT/'codebook.json'),
            'prompt_version':g.prompt.VERSION,'human_review_status':'not_reviewed'})
    g.csvout(g.OUT/'evidence_level_coding.csv',evidence_rows)
    g.csvout(g.OUT/'assigned_category_quotes.csv',assigned)
    g.csvout(g.OUT/'coding_failures.csv',failures,fields=['evidence_id','status','errors'])
    g.dump(g.OUT/'evidence_level_coding.json',evidence_rows)
    panel=aggregate(units,coded,cb)
    g.csvout(g.OUT/'firm_year_content_panel.csv',panel)
    stats,status,pairs=statistics(units,coded,cb,panel)
    queue,integration=review_queue(units,coded,cb)
    examples(units,coded,cb)
    figures(cb,panel,stats,status,pairs)
    costs=accounting()
    protected=g.read(g.STATE/'protected_inputs.json')
    changed=[p for p,h in protected.items() if not (g.ROOT/p).is_file() or g.sha(g.ROOT/p)!=h]
    standard_matches_original=(g.sha(g.ROOT/'docs/implemented_internal_ai_governance_v2.md')==
        g.sha(g.BASE/'classification_standard_snapshot.md')==g.sha(g.OUT/'binary_standard_snapshot.md'))
    original_positive=[r for r in g.rows(g.BASE/'combined_firm_year_v2_panel.csv') if r['implemented_internal_ai_governance_v2']=='1']
    expected={(r['cik'],int(r['fiscal_year'])) for r in original_positive}
    assert {(r['cik'],r['fiscal_year']) for r in panel}==expected
    assert len(panel)==len(expected)
    # Independent set-based audit of every category presence, not the count loop.
    for c in cb['categories']:
        hits={(u['cik'],u['fiscal_year']) for u in units
            if any(v['category_id']==c['id'] for v in coded.get(u['evidence_id'],{}).get(c['dimension'],[]))}
        actual={(r['cik'],r['fiscal_year']) for r in panel if r[c['id']]==1}
        assert hits==actual
    for dim in ('motivations','visions'):
        assert sum(r['count'] for r in status if r['dimension']==dim and r['scope']=='all')==len(panel)
    qa=dict(integrity_passed=not changed and standard_matches_original,
        binary_standard_matches_original_frozen_snapshot=standard_matches_original,
        all_original_positive_firm_years_covered=len(panel)==len(expected),
        original_positive_firm_years=len(expected),panel_rows=len(panel),evidence_input_n=len(units),
        received_validated_evidence_n=len(coded),failed_or_not_submitted_n=len(failures),
        uncodable_evidence_n=sum(x['uncodable'] for x in coded.values()),
        model_review_flag_evidence_n=sum(x['review_flag'] for x in coded.values()),
        flagged_firm_years=sum(r['flagged_evidence_n']>0 for r in panel),
        emerging_theme_evidence_n=sum(bool(x['emerging_themes']) for x in coded.values()),
        assigned_labels=len(assigned),current_quote_validation_failures=0,unknown_category_ids=0,
        source_inputs_modified=changed,protected_file_count=len(protected),
        category_aggregation_set_audit_passed=True,multi_item_dedup_audit_passed=True,
        review_queue_evidence_n=len(queue),review_queue_firm_years=len({(r['cik'],r['fiscal_year']) for r in queue}),
        human_reviews_completed=0,codebook_sha256=g.sha(g.OUT/'codebook.json'),
        caveat='Integrity/traceability checks do not validate semantic classification accuracy or original Item boundaries.',
        reported_utc=g.now())
    events=[json.loads(s) for s in (g.STATE/'request_manifest.jsonl').read_text(encoding='utf-8').splitlines() if s]
    issues=[e for e in events if e['status']=='validation_or_transport_failure']
    qa['historical_validation_or_transport_failures']=len(issues)
    qa['historical_exact_quote_validation_failures']=sum('Quote not exact' in e.get('error','') for e in issues)
    qa['historical_unknown_category_failures']=sum('Unknown or wrong-dimension' in e.get('error','') for e in issues)
    qa['historical_truncated_responses']=sum(e.get('finish_reason')=='length' for e in events if e['status']=='response_received')
    g.csvout(g.OUT/'request_validation_issues.csv',issues,
        fields=['stage','evidence_or_batch_id','request_id','time_utc','status','error'])
    g.dump(g.OUT/'qa.json',qa)
    write_report(cb,panel,stats,status,pairs,costs,qa)
    meta=g.read(g.OUT/'run_manifest.json'); meta.update(stage='reported',reported_utc=g.now(),
        automatic_integrity_passed=qa['integrity_passed'],human_review_pending=True)
    g.dump(g.OUT/'run_manifest.json',meta)
    # Update reproducibility snapshot after final reporting code exists.
    for p in (Path(__file__),g.ROOT/'src/ai_restrictions/governance_content.py',
              g.ROOT/'src/ai_restrictions/llm/content_analysis_prompt.py',
              g.ROOT/'scripts/43_analyze_governance_content.py',
              g.ROOT/'scripts/44_verify_governance_content.py',
              g.ROOT/'tmp/refine_governance_content_codebook.py',
              g.ROOT/'tests/test_governance_content.py'):
        shutil.copyfile(p,g.OUT/'code_snapshot'/p.name)
    outputs={p.relative_to(g.OUT).as_posix():g.sha(p) for p in g.OUT.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'}
    g.dump(g.OUT/'delivery_manifest.json',dict(run_id=g.RUN_ID,created_utc=g.now(),files=outputs,
        intermediate_state=g.STATE.relative_to(g.ROOT).as_posix(),protected_inputs_digest=g.digest(g.canonical(protected).encode())))
    g.log(dict(qa=qa,costs=costs))


def write_report(cb,panel,stats,status,pairs,costs,qa):
    inv=g.read(g.OUT/'data_inventory.json'); n=len(panel)
    overall=[r for r in stats if r['scope']=='all']
    def ranked(dim): return sorted([r for r in overall if r['dimension']==dim],key=lambda r:-r['firm_year_count'])
    cats={c['id']:c for c in cb['categories']}
    def table(dim):
        if dim=='practices':
            head=['|类别|Firm-year N|占全部 Positive %|不同公司数|','|---|---:|---:|---:|']
            return head+[f"|{r['category_id']} {cats[r['category_id']]['name_zh']}|{r['firm_year_count']}|{r['percentage']:.1f}|{r['unique_company_count']}|" for r in ranked(dim)]
        head=['|类别|Firm-year N|占全部 Positive %|显式 N|显式占全部 Positive %|仅隐式 N|',
              '|---|---:|---:|---:|---:|---:|']
        return head+[f"|{r['category_id']} {cats[r['category_id']]['name_zh']}|{r['firm_year_count']}|{r['percentage']:.1f}|{r['explicit_count']}|{r['explicit_percentage']:.1f}|{r['implicit_only_count']}|" for r in ranked(dim)]
    def absent(dim):
        return '；'.join(f"{r['status']}：{r['count']}（{r['percentage']:.1f}%）" for r in status if r['dimension']==dim and r['scope']=='all' and r['count'])
    def toptext(dim):
        return '、'.join(f"{cats[r['category_id']]['name_zh']} {r['firm_year_count']}/{n}（{r['percentage']:.1f}%）" for r in ranked(dim)[:3])
    def explicit_toptext(dim):
        top=sorted(ranked(dim),key=lambda r:-r['explicit_count'])[:3]
        return '、'.join(f"{cats[r['category_id']]['name_zh']} {r['explicit_count']}/{n}（{r['explicit_percentage']:.1f}%）" for r in top)
    evidence_summary=[]
    for dim in ('motivations','visions'):
        ids=[c['id'] for c in cb['categories'] if c['dimension']==dim]
        ex=sum(any(r.get(cid+'_explicit',0) for cid in ids) for r in panel)
        im_only=sum(any(r.get(cid+'_implicit_any',0) for cid in ids) and not any(r.get(cid+'_explicit',0) for cid in ids) for r in panel)
        evidence_summary.append(dict(dimension=dim,any_explicit_firm_years=ex,implicit_only_firm_years=im_only,
            denominator=n,any_explicit_percentage=100*ex/n,implicit_only_percentage=100*im_only/n,
            note='Any supported category label, including partially observed cases; independent of mutually exclusive dimension completeness status.'))
    g.csvout(g.OUT/'dimension_evidence_summary.csv',evidence_summary)
    dimsummary={r['dimension']:r for r in evidence_summary}
    # Post-coding descriptive grouping, explicitly documented rather than new labels.
    risk_goal_ids=['V02','V03','V04','V06','V08','V09']
    positioning=[]
    rset={(r['cik'],r['fiscal_year']) for r in panel if any(r.get(cid+'_explicit',0) for cid in risk_goal_ids)}
    aset={(r['cik'],r['fiscal_year']) for r in panel if r.get('V05_explicit',0)}
    for name,count,definition in [
        ('Listed risk, protection, compliance or reputation objectives',len(rset),'Explicit union of '+','.join(risk_goal_ids)),
        ('AI adoption, innovation or value objective',len(aset),'Explicit V05'),
        ('Both objective families',len(rset&aset),'Intersection of the two explicit unions'),
        ('Neither family explicitly observed',n-len(rset|aset),'No explicit label in either family; does not establish absence of motives/goals')]:
        positioning.append(dict(group=name,count=count,denominator=n,percentage=100*count/n,
            definition=definition,interpretation='Post-coding researcher descriptive grouping, not an LLM category or causal result'))
    g.csvout(g.OUT/'governance_positioning_summary.csv',positioning)
    special_lines=[]
    interpretations={
        '风险缓释案例':'该披露把治理安排与一般风险缓释目的直接联系；引文不证明措施的实际效果。',
        'Responsible / Ethical AI 案例':'该披露说明治理制度与可信、负责任 AI 目标的联系。',
        '治理与 Adoption / Business Value / Innovation 的关联案例':'该披露将治理机制、教育和实验安排与价值目标连接。',
        'practice_without_disclosed_motive_or_vision':'该 firm-year 全部分析证据均未披露动机与目标；实践可识别。未披露不代表不存在。'}
    for e in g.read(g.OUT/'special_examples.json'):
        title=e['type'] if e['type']!='practice_without_disclosed_motive_or_vision' else '实践明确、动机与目标未披露'
        special_lines += [f"### {title}：{e['company_name']} ({e['ticker']}) FY{e['fiscal_year']} {e['source_item']}",'',
            'Observed Disclosure：','', '> '+e['quote'].replace('\n','\n> '),'',
            f"LLM-Based Classification：{e['category_id']}。证据 `{e['evidence_id']}`；原文 `{e['source_path']}`，位置 {e['quote_locations']}。",'',
            'Researcher\'s Interpretation：'+interpretations[e['type']],'']
        if e.get('relationship_quote') and e['relationship_quote']!=e['quote']:
            special_lines += ['治理关联原文：','', '> '+e['relationship_quote'].replace('\n','\n> '),'']
    lines=['# 已实施内部 AI 治理披露：探索性内容分析','',
        '## 1. Executive Summary','',
        f"本研究以正式 V2 的 {n} 个 Positive firm-year（{inv['unique_firms']} 家公司）为固定样本，"
        f"使用 {inv['positive_sections']} 个 Positive 章节中的 {inv['evidence_units']} 条 Binary 支持证据及有界原文上下文。"
        f"DeepSeek 完成 {qa['received_validated_evidence_n']} 条结构化主题编码；其结果属于 LLM-Based Classification。",'',
        f"实践主要集中在：{toptext('practices')}。",'',
        f"动机主要集中在：{toptext('motivations')}。",'',
        f"上述动机频率包含明确支持的隐式标签。只采用显式证据时，前三类为：{explicit_toptext('motivations')}。",'',
        f"目标/愿景主要集中在：{toptext('visions')}。",'',
        f"显式披露所列风控/保护/合规/声誉目标的有 {len(rset)}/{n}（{100*len(rset)/n:.1f}%），"
        f"明确连接 AI 采用、创新或价值目标的有 {len(aset)}/{n}（{100*len(aset)/n:.1f}%），两组重叠 {len(rset&aset)} 个。"
        '这些是特定章节与治理证据窗口内的披露模式，不能解释为企业实际战略重要性的排序。', '',
        f"动机维度分布：{absent('motivations')}。目标/愿景维度分布：{absent('visions')}。",'',
        f"自动完整性校验通过状态：{qa['integrity_passed']}；调用最终失败 {qa['failed_or_not_submitted_n']} 条，"
        f"不可充分编码 {qa['uncodable_evidence_n']} 条；待复核模型标记 {qa['model_review_flag_evidence_n']} 条，"
        f"涉及 {qa['flagged_firm_years']} 个 firm-year。人工审核尚未开展，未报告人工准确率。",'',
        '## 2. Data and Sample','',
        f"年度 Positive firm-years：{inv['annual']}。Item 1A Positive 章节 272 个、Item 7 34 个；"
        '3 个 firm-year 同时在两章 Positive。章节内原始证据分别 354 和 49 条。', '',
        '筛选：正式 combined_firm_year_v2_panel.csv 中 implemented_internal_ai_governance_v2=1。'
        '保留每条原始 Evidence，按其 source hash、accession、Item 与 offset 关联原文；不读取 V1 主题标签。', '',
        '研究范围为原有治理组合证据，以及同一 Positive 章节全部支持片段左右各 1100 字符的连续上下文块；重叠块合并。'
        '原始片段可能分别建立 AI 适用范围、风险背景和治理机制，结合阅读；引文须完整落于一个连续块，禁止跨块拼接。'
        '未对 Negative 章节或整份 10-K 做主题穷尽搜索。'
        'Not Disclosed 仅指该分析文本内未观察到，不能解释为公司没有该动机/目标。', '',
        '完整 Data Inventory、路径、恢复空白标准化记录见 data_inventory.md 和 evidence_source_index.csv。', '',
        '本地 V2 标准、正式 Binary 运行时冻结标准和本次只读副本 SHA-256 一致；没有用后来的规则改写原始分类。', '',
        '## 3. Methodology and Codebook Development','',
        f"探索样本固定为 50 个 firm-year、{inv['exploration_evidence']} 条 Evidence，seed=42；"
        '覆盖全部 11 个 GICS 行业、全部 FY2020–2022 和全部双章节 Positive，兼顾证据长短和章节。'
        '这是目的抽样，不构造概率权重。先逐 firm-year 开放编码，再综合相近主题、检查边界并冻结 Codebook。', '',
        '初轮探索发现部分证据片段无法独立建立治理联系，故在固定样本内对 21 个 firm-year、38 条 Evidence 补充同章上下文开放编码。'
        '初轮 26 个模型复核标记在补充后为 16 个；这属于文本阅读范围纠正，不能作为准确率改善的估计。'
        '初轮结果、补充结果和初稿均保留独立版本。修订区分培训与持续监控，明确正式模型风险框架与具体活动的边界。', '',
        f"冻结类别数：{dict(Counter(c['dimension'] for c in cb['categories']))}。"
        'codebook.md 记录定义、纳入/排除、相邻类别区别及代表引文。代码和 codebook.json 的哈希冻结，'
        '探索样本在全样本阶段同样重新进行闭合编码，未继承开放编码标签。', '',
        '中间层级为 Evidence；最终按 CIK×FY 对每个类别取并集。跨 Evidence 或 Item 相同主题只计一次。'
        '每个标签保留精确引文及原文 offset；动机与目标另要求 relationship_quote。'
        '显式/隐式并存时，单类别统计优先 Explicit；raw_implicit_any 另存保留重叠信息。', '',
        '所有百分比分母明确列入 category_statistics.csv。主分母始终为全部原始 Positive firm-years，'
        '失败、不可编码和复核记录不从分母静默移除。主表为所有通过结构/引文校验的模型标签，'
        'review_flag_sensitivity.csv 另列仅由无模型复核标记 Evidence 支撑的计数。', '',
        '## 4. Governance Practices — Main Findings','']
    lines += table('practices')+['',
        '制度/框架存在性是最常见披露角度；具体治理活动中，测试与风险评估、审批把关、持续监督的频率相近。'
        '政策存在性与具体活动可以在同一观测中共存；这些主题具有不同披露详细度，不能用作治理成熟度评分。','',
        '这些计数描述在已披露治理样本内的主题出现频率；一个 firm-year 可具有多个标签，比例合计可以超过 100%。'
        '类别的广泛出现不能证明治理执行更有效，也不能代表所有上市公司的议题重要性。','',
        '![Governance practices](figures/01_practices_frequency.png)','',
        '## 5. Governance Motivations — Main Findings','']
    lines += table('motivations')+['',absent('motivations'),'','Explicit-only 结果为上表“显式 N”，分母同为 303。'
        '隐式标签只代表文本关系可支持的模型解释；一般 AI 风险段落的邻接不能自动作为治理动机。'
        '每个动机标签的支持引文和关联引文可在 assigned_category_quotes.csv 复核。','',
        f"任一动机具有显式证据的 firm-year 共 {dimsummary['motivations']['any_explicit_firm_years']}"
        f"（{dimsummary['motivations']['any_explicit_percentage']:.1f}%）；仅有隐式动机标签的共 "
        f"{dimsummary['motivations']['implicit_only_firm_years']}（{dimsummary['motivations']['implicit_only_percentage']:.1f}%）。"
        '这些计数包含已观察到的部分证据；维度状态中的 Explicit 为纯显式且完整的互斥分组，Mixed 和 Observed_with_uncertainty 另列，不能把单个状态直接当作任一显式证据总数。','',
        '显式证据口径下，信息/IP 保护、法律合规与负责任/伦理 AI 的频率接近；加入隐式关系后，'
        '法律、数据和模型风险标签的计数更高。结论应分别展示两种口径，避免把风险后果叙述全部当作直接披露的实施原因。','',
        '![Motivations](figures/02_motivations_distribution.png)','',
        '## 6. Governance Objectives / Vision — Main Findings','']
    lines += table('visions')+['',absent('visions'),'','目标维度独立于实践。已生效政策、委员会或控制措施不会自动产生战略愿景标签；'
        '明确表达的未来治理目标可以进入目标维度，未来计划不能作为已实施实践。'
        '与 Adoption、Innovation 或价值创造的联系必须由治理相关目的/职责表述支持。','',
        f"任一目标具有显式证据的 firm-year 共 {dimsummary['visions']['any_explicit_firm_years']}"
        f"（{dimsummary['visions']['any_explicit_percentage']:.1f}%）；仅有隐式目标标签的共 "
        f"{dimsummary['visions']['implicit_only_firm_years']}（{dimsummary['visions']['implicit_only_percentage']:.1f}%）。",'',
        '### 风控/合规与 AI 赋能定位的描述性比较','',
        '以下为冻结编码之后的研究者描述性归组，未增设 LLM 标签。所列风控/保护/合规/声誉目标取 '
        'V02、V03、V04、V06、V08、V09 的显式证据并集；采用/创新/价值目标为显式 V05。'
        'V01 规范性 Responsible AI 与 V07 可解释/专家验证目标另外报告，不强行归入这两组。','',
        '|目标组|Firm-year N|占全部 Positive %|','|---|---:|---:|',
        *[f"|{r['group']}|{r['count']}|{r['percentage']:.1f}|" for r in positioning],'',
        (f"观察到 {len(rset&aset)} 个 firm-year 同时明确披露所列风控/合规等目标与 AI 采用/创新/价值目标，"
         '说明在这部分披露中两类定位可以并存。' if rset&aset else
         '当前显式编码未观察到这两组目标在同一 firm-year 并存；这只说明所分析文本内的披露情况。'),
        '“Neither”表示未观察到上述两组的显式标签，可以包括未披露、隐式、其他目标或未解决内容，不能解释为没有战略或治理目标。','',
        '所分析文本以 Item 1A 为主，且证据最初为识别治理而收集；风险与合规的显式关联更常见，'
        '与章节功能和证据选择均有关。9 个 AI 赋能目标披露说明这类联系确实存在，较低频率不能证明其他企业不重视 AI 创新或价值。','',
        '![Vision](figures/03_visions_distribution.png)','',
        '## 7. Cross-Dimension Patterns','']
    for d1,d2,title in [('practices','practices','实践共同披露'),('practices','motivations','实践与显式动机'),('motivations','visions','显式动机与显式目标')]:
        ps=[r for r in pairs if r['dimension_1']==d1 and r['dimension_2']==d2 and
            (d1!=d2 or r['category_1']<r['category_2'])]
        best=sorted(ps,key=lambda r:-r['count'])[:5]
        lines += [f'### {title}','']
        lines += [f"- {cats[r['category_1']]['name_zh']} × {cats[r['category_2']]['name_zh']}：{r['count']} 个 firm-year（占全部 Positive {r['percentage_all_positive']:.1f}%）；行条件比例 {r['row_conditional_percentage']:.1f}%。" for r in best if r['count']]
        lines += ['']
    lines += ['上述跨维度计数基于同一 firm-year 共同披露，不保证每种实践与每种动机之间都有逐对直接因果/目的联系。'
        '同一目的语句可能分别支持动机和目标；这些维度的共同出现部分来自共享措辞与概念联系，不能解释为独立行为机制。'
        '不作回归、因果推断或治理效果判断。','',
        '年度主题表使用每年 Positive 内部比例；FY2020、FY2021、FY2022 分别仅 2、2、3 个观测。'
        '年度间样本公司、章节和披露长度均有变化，组合效应显著限制趋势解释。重复公司跨年披露也会影响频率。','',
        '例如 FY2023–FY2025 测试/评估类的年内比例为 22.9%、16.1%、13.1%，对应绝对观测数为 8、15、22；'
        '比例下降与数量增加可以同时发生，不能据此断言企业实际评估活动减少。','',
        '![Annual themes](figures/04_practices_by_year.png)','',
        '![Co-disclosure](figures/05_practices_cooccurrence.png)','',
        '![Practice and motivation](figures/06_practices_motivations.png)','',
        'Item 图分别使用章内 Positive firm-year 分母 272 和 34；原始计数与占全部 303 的比例同时保留。'
        '不同章节的公司构成和披露功能不同，差异不能单纯归因于章节本身。','',
        '![Item topics](figures/07_item_topic_distribution.png)','',
        '## 8. Representative Disclosure Examples','',
        '每类 2–3 个不同公司真实示例（有充分材料时）见 representative_examples.md，含原始引文、'
        '公司、年份、章节、Evidence ID、offset 与解释。另列风险缓释、Responsible/Ethical AI、'
        'Adoption/Business Value/Innovation 关联，以及实践明确但动机/目标未披露的案例。证据不足不强行补足。','',
        *special_lines,
        '## 9. Limitations and Validation','',
        f"- 原始 Positive firm-year 覆盖：{qa['panel_rows']}/{qa['original_positive_firm_years']}。",
        f"- Evidence 输入/成功结构化编码：{qa['evidence_input_n']}/{qa['received_validated_evidence_n']}；未提交/最终失败 {qa['failed_or_not_submitted_n']}。",
        f"- 不可编码 {qa['uncodable_evidence_n']}；模型复核标记 {qa['model_review_flag_evidence_n']}；模型提议 Emerging Theme Evidence {qa['emerging_theme_evidence_n']}（尚未确认为新类别）。",
        f"- 已分配标签 {qa['assigned_labels']}；最终未知类别 ID {qa['unknown_category_ids']}；最终引用验证失败 {qa['current_quote_validation_failures']}。",
        f"- 待人工复核队列 {qa['review_queue_evidence_n']} 条（{qa['review_queue_firm_years']} 个 firm-year）；包括随机 30 个 firm-year 的全部证据、隐式关系边界样本及全部模型标记。",
        f"- 输入保护：{qa['protected_file_count']} 个输入/源文件哈希复核，修改数量 {len(qa['source_inputs_modified'])}。",
        '- Item→firm-year 每类别并集与独立集合计数逐项对账通过；双章节重复不重复计数。', '',
        '17 项离线测试通过，覆盖引文连续性、类别/关联校验、失败保留和去重聚合；另以独立脚本核验导出 CSV/JSON、原文哈希和全部已分配引文。'
        '证据见 offline_test_summary.json、independent_qa.json。','',
        'Emerging Theme 为模型提议，部分可能属于既有类别的证据不足或边界歧义，需人工确认其新颖性；'
        '本次未据此新增全样本类别。个别 Binary 支持片段在本次内容编码中仍无法解释，保留不可编码与复核状态，'
        '不改写原有 Positive，也不将其内容主题缺失强制解释为不存在。', '',
        f"历史结构/传输失败事件 {qa['historical_validation_or_transport_failures']} 次，"
        f"其中精确引用校验失败 {qa['historical_exact_quote_validation_failures']} 次、未知类别 {qa['historical_unknown_category_failures']} 次；"
        '事件清单见 request_validation_issues.csv。失败、重试和引用纠正保留于 request_manifest.jsonl 与 raw responses，最终失败表不会静默丢行。'
        'quote validation 保证文本存在，不能证明标签语义正确。原有 V2 二元判定和 Item 边界未重新人工验证。', '',
        'Disclosure Content ≠ Actual Corporate Behavior。Observed Disclosure 为可追溯原文；'
        'LLM-Based Classification 为主题与显隐关系标签；Researcher\'s Interpretation 为对频率和共同披露的谨慎解读。'
        '本次未完成独立人工复核，不报告准确率、intercoder reliability 或将自洽性当作准确率。', '',
        '## 10. LLM Configuration, Token Usage and Cost','',
        '使用现有共享 DeepSeek chat_json 客户端及凭证解析；请求 alias=deepseek-flash，temperature=0，'
        'max_tokens=16384，JSON object，timeout=120s，3 次 transport retry（2/4/8 秒），并发 16，'
        '每次执行最多 2 次结构/引用纠正请求，总恢复请求有限。缓存按精确 payload 哈希验证，断点续跑复用成功。', '',
        f"Codebook 单次综合步骤因默认上限截断，单独将 max_tokens 提高至 65536；历史截断响应 {qa['historical_truncated_responses']} 次。"
        '这些响应未进入编码数据，其 API usage 全部计入成本。初次综合请求的 JSON 格式指令也已显式补足，原始失败保留。', '',
        '原流程 intended model=DeepSeek-V4.1-Flash；2026-10-18 官方页面为 DeepSeek-V4.1-Flash-1017。'
        '保留同一 API alias，并明确记录 provider 更新。实际返回模型：'+g.canonical(costs['returned_models'])+'。', '',
        f"API transport attempts={costs['api_attempts']}；received responses={costs['received_responses']}；"
        f"分阶段请求={costs['by_stage']}；未取得 token usage 的尝试={costs['attempts_without_usage_response']}"
        f"（含 HTTP 拒绝 {costs['http_error_attempts']}、网络失败或中断请求）。", '',
        'Token usage（包含收到响应的重试）：'+g.canonical(costs['usage'])+'；'
        f"其中 API 返回 reasoning_tokens={costs['reasoning_tokens']}，已包含在 completion_tokens 中，不重复计费求和。", '',
        f"运行事件 UTC 起止：{costs['earliest_event_utc']} — {costs['latest_event_utc']}；"
        f"API 工作流墙钟约 {costs.get('wall_clock_seconds',0)/60:.1f} 分钟。", '',
        'USD 公开单价估算情景：'+g.canonical(costs['USD_published_price_scenarios'])+'。'
        '本次周日按官方时段属于 off-peak；没有取得账户逐笔账单，因此实际扣费保留 null。'
        '未返回 usage 的失败尝试不能自行补算。', '',
        '价格与模型版本来源：[DeepSeek 官方 Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)，'
        '查询日期 2026-10-18。快照及计算依据见 pricing_snapshot.json、cost_and_token_summary.json。', '',
        '复现入口：scripts/43_analyze_governance_content.py。实际阶段为 prepare → 初轮 open → 初稿 synthesize → supplement → 修订 synthesize → '
        '研究者检查 draft → freeze → pilot → full → report。report 只读取缓存并重建派生交付，不发付费请求。'
        '完整中间状态路径见 run_manifest.json；文件哈希清单见 delivery_manifest.json。','']
    (g.OUT/'run_report.md').write_text('\n'.join(lines),encoding='utf-8')
