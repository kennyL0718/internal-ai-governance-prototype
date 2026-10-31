"""Read-only classifications -> source-reconciled academic PNG/PDF figures.

No LLM, classification, network or existing-report writers are imported.
The complete module is also a standalone reproducible script inside its bundle.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import textwrap
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file() and (p/'src/ai_restrictions').is_dir())
RUN='governance_purpose_inductive_v1_20261025'
NAME=RUN+'_visualization_20261026'
DEFAULT_OUT=ROOT/'outputs/figures'/NAME
NAVY='#285A7C'
PALETTE=['#285A7C','#C87935','#40876C','#A25986','#7970A6','#C9A240','#5F8C9C',
         '#A96659','#6F7846','#666A78','#8BB2D0','#D8A4B9','#8EBCAE','#ADA0C8','#C4B17C']

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvout(p,data,fields=None):
    fields=fields or list(data[0])
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
def check(condition,message):
    if not condition:raise ValueError(message)
def wrap(s,width):return '\n'.join(textwrap.wrap(s,width=width,break_long_words=False,break_on_hyphens=False))

def load_data(run=RUN):
    state=ROOT/'data/interim/classifications'/run
    report=ROOT/'outputs/reports'/run;tables=ROOT/'outputs/tables'/run
    paths=[state/n for n in ('firm_year_classification.csv','evidence_level_classification.csv','codebook.json','codebook_freeze.json')]
    paths += [report/n for n in ('summary.json','verification.json','delivery_manifest.json','inductive_codebook.md','run_report.md')]
    paths += [tables/n for n in ('theme_frequency.csv','annual_theme_distribution.csv','theme_cooccurrence.csv','status_summary.csv')]
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    manifest=read(report/'delivery_manifest.json');expected={a['path']:a['sha256'] for a in manifest['artifacts']}
    for p,h in inputs.items():
        if p.endswith('/delivery_manifest.json'):continue
        check(expected.get(p)==h,'Source does not match delivered classification hash: '+p)
    check(read(report/'verification.json')['passed'],'Existing classification QA did not pass')
    book=read(state/'codebook.json');freeze=read(state/'codebook_freeze.json')
    check(sha(state/'codebook.json')==freeze['codebook_sha256'],'Frozen codebook hash mismatch')
    themes={t['id']:t['name'] for t in book['themes']};ids=list(themes)
    panel=rows(state/'firm_year_classification.csv');byid={r['unit_id']:r for r in panel}
    check(len(byid)==len(panel),'Duplicate unit IDs')
    check(len({(r['cik'],r['fiscal_year']) for r in panel})==len(panel),'Duplicate CIK/fiscal-year')
    labels={};statuses=Counter()
    for r in panel:
        ls=json.loads(r['verified_themes']);check(len(ls)==len(set(ls)),'Duplicate firm-year theme')
        check(set(ls)<=set(ids),'Unknown theme');labels[r['unit_id']]=set(ls);statuses[r['status']]+=1
        check(r['classification_status']=='complete' and r['semantic_qa_status']=='complete','Incomplete classification/QA')
        if r['qa_passed']=='True':
            check(r['status'] in ('explicit_purpose','no_explicit_purpose'),'Unexpected QA-passed status')
            check(bool(ls)==(r['status']=='explicit_purpose'),'Explicit-purpose status inconsistency')
            check(all(r[t]==str(int(t in ls)) for t in ids),'Theme columns differ from verified labels')
        else:
            check(not ls and all(r[t]=='' for t in ids),'Unresolved labels entered main counts')
    evidence=rows(state/'evidence_level_classification.csv');support=set();support_ids=[]
    for e in evidence:
        if e['counted']!='True':continue
        check(e['source_verified']=='True' and e['semantic_verdict']=='accept' and e['uncertain']=='False','Unverified evidence counted')
        check(e['theme_id'] in labels[e['unit_id']],'Evidence/panel label mismatch')
        check(byid[e['unit_id']]['qa_passed']=='True','Exception evidence counted')
        support.add((e['unit_id'],e['theme_id']))
        support_ids.append((e['unit_id'],e['theme_id'],e['input_sha256'],e['relationship_quote']))
    check(len(set(support_ids))==len(support_ids),'Duplicate counted support passages')
    check(support=={(u,t) for u,ts in labels.items() for t in ts},'Panel label lacks verified evidence')
    n=len(panel);freq=Counter(t for ts in labels.values() for t in ts)
    order=sorted(ids,key=lambda t:(-freq[t],t))
    masters=rows(tables/'theme_frequency.csv')
    check({r['theme_id'] for r in masters}==set(ids),'Master theme coverage mismatch')
    for r in masters:
        t=r['theme_id'];check(r['theme_name']==themes[t],'Theme renamed')
        check(int(r['firm_year_count'])==freq[t] and int(r['positive_denominator'])==n,'Master frequency mismatch')
        check(abs(float(r['share_all_positive'])-freq[t]/n)<1e-12,'Master prevalence mismatch')
    years=sorted({int(r['fiscal_year']) for r in panel});annual=[];metrics=[]
    for y in years:
        ps=[r for r in panel if int(r['fiscal_year'])==y];counts={t:sum(t in labels[r['unit_id']] for r in ps) for t in ids}
        total=sum(counts.values());explicit=sum(bool(labels[r['unit_id']]) for r in ps)
        check(total>0,'No verified annual assignments; composition requires explicit missing-year handling')
        a=dict(fiscal_year=y,positive_n=len(ps),qa_passed_n=sum(r['qa_passed']=='True' for r in ps),
            explicit_n=explicit,no_explicit_n=sum(r['status']=='no_explicit_purpose' for r in ps),
            exception_n=sum(r['qa_passed']!='True' for r in ps),assignments=total,explicit_rate=explicit/len(ps),counts=counts)
        check(a['explicit_n']+a['no_explicit_n']+a['exception_n']==len(ps),'Annual statuses do not reconcile')
        annual.append(a)
        for t in order:metrics.append(dict(fiscal_year=y,theme_id=t,theme_name=themes[t],firm_year_count=counts[t],
            positive_firm_year_denominator=len(ps),firm_year_prevalence=counts[t]/len(ps),
            total_theme_assignments=total,theme_assignment_share=counts[t]/total))
    lk={(m['fiscal_year'],m['theme_id']):m for m in metrics}
    for r in rows(tables/'annual_theme_distribution.csv'):
        m=lk[int(r['fiscal_year']),r['theme_id']]
        check(int(r['firm_year_count'])==m['firm_year_count'] and int(r['positive_denominator'])==m['positive_firm_year_denominator'],'Master annual count mismatch')
        check(abs(float(r['share_all_positive'])-m['firm_year_prevalence'])<1e-12,'Master annual prevalence mismatch')
    co={(a,b):sum(a in ts and b in ts for ts in labels.values()) for a in ids for b in ids}
    for r in rows(tables/'theme_cooccurrence.csv'):
        check(co[r['theme_a'],r['theme_b']]==int(r['firm_year_count']) and int(r['positive_denominator'])==n,'Master co-occurrence mismatch')
    summary=read(report/'summary.json')
    check((n,sum(bool(ts) for ts in labels.values()),sum(r['qa_passed']=='True' for r in panel))==
        (summary['positive_firm_years'],summary['explicit_purpose_firm_years'],summary['qa_passed_firm_years']),'Master summary mismatch')
    check(sum(freq.values())==sum(a['assignments'] for a in annual)==len(support),'Assignment totals do not reconcile')
    return dict(run=run,inputs=inputs,panel=panel,themes=themes,order=order,years=years,n=n,freq=freq,
        annual=annual,metrics=metrics,co=co,summary=summary,assignment_n=sum(freq.values()),
        support_passages=len(support_ids),multi_label_n=sum(len(ts)>1 for ts in labels.values()))

def configure(out):
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/mpl_purpose_visualization_20261026'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'axes.labelsize':11,
        'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,
        'figure.facecolor':'white','savefig.facecolor':'white','axes.unicode_minus':False})
    return plt

def title(fig,heading,subtitle):
    fig.text(.045,.965,heading,fontsize=18,weight='bold',va='top')
    fig.text(.045,.925,subtitle,fontsize=10.5,color='#4B5563',va='top')
def footer(fig,note):fig.text(.045,.032,note,fontsize=9,color='#4B5563',va='bottom',linespacing=1.55)
def grid(ax,axis='y'):ax.grid(axis=axis,color='#D5D9DC',alpha=.55,linewidth=.7);ax.set_axisbelow(True)

def save(fig,name,out,audits):
    import matplotlib.pyplot as plt
    fig.canvas.draw();renderer=fig.canvas.get_renderer();width,height=fig.canvas.get_width_height()
    texts=list(fig.texts)
    for ax in fig.axes:
        xlo,xhi=sorted(ax.get_xlim());ylo,yhi=sorted(ax.get_ylim())
        xt=[t for v,t in zip(ax.get_xticks(),ax.get_xticklabels()) if xlo<=v<=xhi]
        yt=[t for v,t in zip(ax.get_yticks(),ax.get_yticklabels()) if ylo<=v<=yhi]
        texts += list(ax.texts)+xt+yt+[ax.title,ax.xaxis.label,ax.yaxis.label]
    for ax in fig.axes:
        legend=ax.get_legend()
        if legend:texts+=legend.get_texts()
    clipped=[]
    for t in texts:
        if not t.get_visible() or not t.get_text():continue
        b=t.get_window_extent(renderer)
        if b.x0< -2 or b.y0< -2 or b.x1>width+2 or b.y1>height+2:clipped.append(t.get_text())
    check(not clipped,'Text outside figure canvas '+name+': '+repr(clipped))
    fig.savefig(out/(name+'.png'),dpi=300,facecolor='white')
    fig.savefig(out/(name+'.pdf'),facecolor='white',metadata={
        'Creator':'Matplotlib / governance purpose visualization','CreationDate':None,'ModDate':None})
    audits[name]=dict(text_canvas_check=True,axes=len(fig.axes),png_dpi=300,
        width_inches=fig.get_figwidth(),height_inches=fig.get_figheight(),data_values_checked=True)
    plt.close(fig)

def legend_axis(fig,d,colors,hatches):
    from matplotlib.patches import Patch
    ax=fig.add_axes([.575,.16,.405,.72]);ax.axis('off')
    ax.legend([Patch(facecolor=colors[t],edgecolor='white',hatch=hatches[t]) for t in d['order']],
        [wrap(t+'  '+d['themes'][t],49) for t in d['order']],loc='upper left',frameon=False,
        fontsize=9.2,handlelength=1.8,handleheight=1.1,labelspacing=.9,borderaxespad=0)

def figures(d,out):
    plt=configure(out)
    import numpy as np
    from matplotlib.ticker import PercentFormatter,MaxNLocator
    from matplotlib.colors import to_rgb
    colors={t:PALETTE[i] for i,t in enumerate(d['themes'])};hatches={t:('//' if i>=10 else '') for i,t in enumerate(d['themes'])}
    audit={};order=d['order'];years=d['years'];annual=d['annual'];n=d['n']
    csvout(out/'theme_color_map.csv',[dict(theme_id=t,theme_name=d['themes'][t],color=colors[t],hatch=hatches[t],legend_order=i+1) for i,t in enumerate(order)])
    # Figure 1: match the original Disclosed governance practices bar styling.
    fig=plt.figure(figsize=(14.5,11));ax=fig.add_axes([.425,.145,.53,.735])
    title(fig,'Distribution of governance purpose themes','Figure 1  |  QA-verified explicit evidence  |  FY2020–FY2025')
    values=[d['freq'][t] for t in order];bars=ax.barh(range(len(order)),values,color=NAVY,height=.64)
    ax.set_yticks(range(len(order)),[wrap(t+'  '+d['themes'][t],54) for t in order],fontsize=10.2)
    ax.invert_yaxis();ax.set_xlim(0,max(values)*1.28);ax.set_xlabel('Firm-year observations');grid(ax,'x')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True,nbins=7));ax.tick_params(axis='y',length=0,pad=9)
    for i,v in enumerate(values):ax.text(v+.8,i,f'{v}  ({v/n:.1%})',va='center',fontsize=10)
    check([b.get_width() for b in bars]==values,'Figure 1 bar mismatch')
    footer(fig,f'Denominator: all {n} governance-Positive firm-years, matching the main statistics. Verified labels only.\n'
        'Multi-label: one count per firm-year per theme; percentages may sum above 100%.\n'
        'No-explicit-purpose and exception observations remain in the denominator and contribute no theme assignments.')
    save(fig,'01_theme_distribution',out,audit)
    # Figures 2a and 2b: one fixed legend/color/stack order, different units.
    x=np.arange(len(years));counts=np.array([[a['counts'][t] for a in annual] for t in order]);totals=counts.sum(axis=0)
    shares=counts/totals
    check(np.allclose(shares.sum(axis=0),1),'Annual composition is not 100%')
    for normalized,name in [(True,'02a_annual_assignment_composition'),(False,'02b_annual_theme_counts')]:
        fig=plt.figure(figsize=(16,10.8));ax=fig.add_axes([.08,.185,.45,.66])
        title(fig,'Annual composition of governance purposes' if normalized else 'Annual governance purpose theme counts',
            'Figure 2a  |  Share of annual theme assignments' if normalized else 'Figure 2b  |  Firm-year counts within each theme')
        matrix=shares if normalized else counts;bottom=np.zeros(len(years))
        ax.axvspan(-.48,2.48,color='#F0F2F3',zorder=0)
        for t,vals in zip(order,matrix):
            bars=ax.bar(x,vals,bottom=bottom,color=colors[t],width=.67,edgecolor='white',linewidth=.5,hatch=hatches[t],zorder=3)
            check(np.allclose([b.get_height() for b in bars],vals),'Figure 2 stacked segment mismatch')
            for j,v in enumerate(vals):
                threshold=.067 if normalized else max(totals)*.06
                if v>=threshold:
                    lum=sum(a*b for a,b in zip(to_rgb(colors[t]),(.2126,.7152,.0722)))
                    text=f'{t}\n{v:.0%}' if normalized else f'{t}\n{int(v)}'
                    ax.text(j,bottom[j]+v/2,text,ha='center',va='center',fontsize=8.3,color='white' if lum<.55 else '#17202A',zorder=4)
            bottom+=vals
        for j,a in enumerate(annual):ax.text(j,1.022 if normalized else totals[j]+max(totals)*.025,
            f"A={a['assignments']}",ha='center',va='bottom',fontsize=9.5)
        ax.set_xticks(x,[str(y) for y in years]);ax.set_xlabel('Fiscal year',labelpad=11)
        if normalized:
            ax.set_ylim(0,1.09);ax.set_yticks(np.arange(0,1.01,.2));ax.yaxis.set_major_formatter(PercentFormatter(1))
            ax.set_ylabel('Share of annual theme assignments (%)')
        else:
            ax.set_ylim(0,max(totals)*1.14);ax.set_ylabel('Firm-year observations by theme');ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        grid(ax);legend_axis(fig,d,colors,hatches)
        footer(fig,('Composition denominator: A = sum of QA-verified firm-year–theme assignments in each fiscal year.\n' if normalized else
            'Each segment counts QA-verified firm-years with that theme; stacked totals are theme assignments, not distinct firms.\n')+
            f"Total across years: {d['assignment_n']} assignments. One count per firm-year per theme; all 15 themes retained.\n"+
            'Shaded FY2020–FY2022 have only 2–3 governance-Positive firm-years each. Composition and prevalence use different denominators.')
        save(fig,name,out,audit)
    # Figure 3: small-multiple lines keep all 15 original names legible.
    fig,axes=plt.subplots(5,3,figsize=(18,16),sharex=True,sharey=True)
    fig.subplots_adjust(left=.065,right=.975,bottom=.13,top=.865,hspace=.80,wspace=.20)
    title(fig,'Annual theme prevalence','Figure 3  |  Verified firm-years with a theme / all governance-Positive firm-years in that fiscal year')
    peak=max(a['counts'][t]/a['positive_n'] for a in annual for t in order)
    ceiling=min(1,max(.10,math.ceil(peak*10)/10+.1))
    for ax,t in zip(axes.flat,order):
        vals=[a['counts'][t]/a['positive_n'] for a in annual]
        ax.axvspan(2019.8,2022.4,color='#F0F2F3')
        line,=ax.plot(years,vals,color=colors[t],marker='o',linewidth=1.8,markersize=4.5)
        check(list(line.get_ydata())==vals,'Prevalence line mismatch')
        ax.set_title(wrap(t+'  '+d['themes'][t],49),loc='left',fontsize=10.2,pad=9)
        ax.set_ylim(0,ceiling);ax.set_xticks(years);ax.set_xticklabels([str(y) for y in years],fontsize=9)
        ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0));grid(ax)
    fig.supylabel('Annual firm-year prevalence (%)',x=.015,fontsize=11)
    footer(fig,'Annual governance-Positive denominators: '+', '.join(f"FY{a['fiscal_year']} N={a['positive_n']}" for a in annual)+'.\n'
        'Verified labels only; no-explicit-purpose and exception observations remain in annual denominators. Multi-label.\n'
        'Identical y-axis scales across themes. Shading marks years with only 2–3 observations; small early samples limit trend interpretation.')
    save(fig,'03_annual_theme_prevalence',out,audit)
    # Figure 4: joint counts off diagonal; gray diagonal contains marginal N.
    matrix=np.array([[d['co'][a,b] for b in order] for a in order]);masked=np.ma.array(matrix,mask=np.eye(len(order),dtype=bool))
    fig=plt.figure(figsize=(16,12.3));ax=fig.add_axes([.38,.19,.54,.65])
    title(fig,'Governance purpose theme co-occurrence','Figure 4  |  Jointly assigned, QA-verified firm-year observations')
    cmap=plt.get_cmap('Blues').copy();cmap.set_bad('#E7E9EC');maximum=max(1,int(masked.max()))
    edges=np.arange(len(order)+1)-.5
    im=ax.pcolormesh(edges,edges,masked,cmap=cmap,vmin=0,vmax=maximum,shading='flat',rasterized=False)
    ax.set(xlim=(-.5,len(order)-.5),ylim=(len(order)-.5,-.5),aspect='equal')
    ax.set_yticks(range(len(order)),[wrap(t+'  '+d['themes'][t],48) for t in order],fontsize=9)
    ax.set_xticks(range(len(order)),order,fontsize=9);ax.tick_params(length=0)
    for i in range(len(order)):
        for j in range(len(order)):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=9,
                color='white' if i!=j and matrix[i,j]>maximum*.58 else '#202932')
    ax.set_xticks(np.arange(-.5,len(order),1),minor=True);ax.set_yticks(np.arange(-.5,len(order),1),minor=True)
    ax.grid(which='minor',color='white',linewidth=.7);ax.tick_params(which='minor',length=0)
    cax=fig.add_axes([.935,.25,.014,.52]);cb=fig.colorbar(im,cax=cax,label='Joint firm-year count')
    if cb.solids is not None:cb.solids.set_rasterized(False)
    footer(fig,f'Off-diagonal cells: distinct firm-years with both themes; reference denominator = all {n} governance-Positive firm-years.\n'
        'Gray diagonal: marginal count for each theme; diagonal is excluded from the color scale. Symmetric matrix; multi-label.\n'
        'Only QA-verified explicit labels contribute. Co-occurrence describes disclosures and does not establish causal relationships.')
    save(fig,'04_theme_cooccurrence',out,audit)
    # Figure 5: confirmed disclosure rate; unresolved observations remain visible.
    fig=plt.figure(figsize=(12,7.5));ax=fig.add_axes([.09,.25,.86,.60])
    title(fig,'Explicit governance purpose disclosure rate','Figure 5  |  QA-verified explicit-purpose firm-years / all governance-Positive firm-years')
    vals=[a['explicit_rate'] for a in annual];ax.axvspan(2019.8,2022.4,color='#F0F2F3')
    line,=ax.plot(years,vals,color=NAVY,marker='o',markersize=7,linewidth=2)
    check(list(line.get_ydata())==vals,'Disclosure rate line mismatch')
    for a,v in zip(annual,vals):ax.annotate(f"{a['explicit_n']}/{a['positive_n']}  ({v:.1%})",(a['fiscal_year'],v),
        xytext=(0,13),textcoords='offset points',ha='center',fontsize=10)
    ax.set_ylim(0,1.16);ax.set_yticks(np.arange(0,1.01,.2));ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xticks(years,[f"{a['fiscal_year']}\nN={a['positive_n']}" for a in annual]);ax.set_xlabel('Fiscal year',labelpad=9)
    ax.set_ylabel('Verified explicit-purpose disclosure rate (%)');grid(ax)
    footer(fig,'Annual exception counts: '+', '.join(f"{a['fiscal_year']}: {a['exception_n']}" for a in annual)+'.\n'
        f"Overall: {d['summary']['explicit_purpose_firm_years']}/{n} = {d['summary']['explicit_purpose_firm_years']/n:.1%}. Exceptions contribute no verified-positive numerator and retain unresolved status.\n"+
        'Shaded early years have only 2–3 observations. Rates describe observed disclosures in the governance-Positive sample.')
    save(fig,'05_explicit_purpose_disclosure_rate',out,audit)
    return audit,colors

def write_report(d,out,qa):
    s=d['summary'];annual=d['annual'];first=next(a for a in annual if a['fiscal_year']==2023);last=annual[-1]
    lines=['# AI Governance Purpose 可视化分析',f'Visualization ID: `{out.name}`；来源分类 Run: `{d["run"]}`。',
        '## 数据来源与口径',
        f"使用 `data/interim/classifications/{d['run']}/firm_year_classification.csv`、`evidence_level_classification.csv` 和冻结 `codebook.json`，并逐项核对 `outputs/tables/{d['run']}/` 的主题频率、年度分布与共现主表。",
        f"样本 {d['n']} 个 Governance Positive firm-years、{s['distinct_firms']} 家公司、15个原主题。显性目的且通过 QA：{s['explicit_purpose_firm_years']}（{s['explicit_purpose_firm_years']/d['n']:.1%}）；无显性目的：{s['no_explicit_purpose_firm_years']}；待复核：{s['exception_firm_years']}。主题分子仅使用 `qa_passed=True` 的 `verified_themes`，并与 `counted=True / source_verified=True / semantic_verdict=accept` 原文支持逐一对应。",
        f"多标签按 CIK×Fiscal Year×Theme 去重；Item 1A/Item 7 证据不重复计算。同一 firm-year 可对应多主题。合计 {d['assignment_n']} 个不同 firm-year–theme assignments，{d['multi_label_n']} 个 firm-years 拥有多个主题。主统计分母保留全部303个Positive；52个待复核观察不贡献主题分子，其原始状态保持未决。",
        '## 图表定义与计算',
        '|图|文件（PNG/PDF）|分子与分母|','|---|---|---|',
        '|Figure 1|01_theme_distribution|每个主题的已验证 firm-year 数 / 全部303个Positive firm-years；降序，末端标Count和Percentage。|',
        '|Figure 2a|02a_annual_assignment_composition|n(y,t) / Σt n(y,t)。每年全部已验证主题分配次数作分母，组成之和为100%。|',
        '|Figure 2b|02b_annual_theme_counts|n(y,t)绝对数；每年堆叠高度是Theme Assignments，允许同一firm-year跨主题出现。|',
        '|Figure 3|03_annual_theme_prevalence|n(y,t) / N(y)，N(y)为当年全部Governance Positive；15个小面板折线，统一y轴。|',
        '|Figure 4|04_theme_cooccurrence|同一firm-year同时拥有两主题的联合次数；参照样本303。灰色对角线是主题边际次数，不参与色阶。|',
        '|Figure 5|05_explicit_purpose_disclosure_rate|当年至少一个已验证显性目的的firm-years / 当年全部Governance Positive。|','',
        '**Theme Assignment Share** 衡量已验证标签的构成；**Firm-year Prevalence** 衡量主题在当年Positive观察中的覆盖。Figure 2a采用前者，Figure 1/3/5采用firm-year分母。Figure 2b的堆叠总高度也不表示独立firm-years数量。',
        '## 主要描述性结果',
        '主题频率最高的三类为：'+ '；'.join(f"{t} {d['themes'][t]}：{d['freq'][t]}（{d['freq'][t]/d['n']:.1%}）" for t in d['order'][:3])+'。',
        '|Fiscal Year|Positive N|有显性目的|无显性目的|待复核|Theme Assignments|显性目的率|','|---|---:|---:|---:|---:|---:|---:|']
    for a in annual:lines.append(f"|{a['fiscal_year']}|{a['positive_n']}|{a['explicit_n']}|{a['no_explicit_n']}|{a['exception_n']}|{a['assignments']}|{a['explicit_rate']:.1%}|")
    lines += ['',f"FY2023–FY{last['fiscal_year']} 的已验证 Theme Assignments 从 {first['assignments']} 增至 {last['assignments']}；同期 Governance Positive 分母从 {first['positive_n']} 增至 {last['positive_n']}，需要结合 prevalence 解读绝对数变化。",'']
    for y in (2023,2024,2025):
        a=next(x for x in annual if x['fiscal_year']==y)
        ranking=sorted(d['order'],key=lambda t:(-a['counts'][t],t));cutoff=a['counts'][ranking[2]]
        top=[t for t in ranking if a['counts'][t]>=cutoff]
        lines.append(f"FY{y} 的组成前三位（含并列）："+'；'.join(f"{t} {a['counts'][t]}/{a['assignments']} = {a['counts'][t]/a['assignments']:.1%}" for t in top)+'。')
    lines+=['','FY2023→FY2025 的主题组成变化：'+ '；'.join(
        f"{t} {first['counts'][t]/first['assignments']:.1%}→{last['counts'][t]/last['assignments']:.1%}"
        for t in ('T01','T05','T06'))+'。对应的年度 firm-year prevalence 为：'+ '；'.join(
        f"{t} {first['counts'][t]/first['positive_n']:.1%}→{last['counts'][t]/last['positive_n']:.1%}"
        for t in ('T01','T05','T06'))+'。',
        f"FY2023、FY2024、FY2025 的已验证显性目的披露率分别为 {first['explicit_rate']:.1%}、{annual[-2]['explicit_rate']:.1%}、{last['explicit_rate']:.1%}。"]
    pair=sorted([(d['co'][a,b],a,b) for a,b in combinations(d['order'],2)],reverse=True)[0]
    lines += ['',f"最高的非对角共现为 {pair[1]} 与 {pair[2]}：{pair[0]} 个 firm-years（占303的{pair[0]/d['n']:.1%}）。",
        'FY2020–FY2022 每年仅2–3个观察。早期组成与比例受个别企业影响很大，图中以灰色背景提示；年度差异描述样本披露构成，不能解释为企业目的或治理效果发生因果变化。自动分类和语义QA尚未替代人工裁决。',
        '## 一致性与 QA',
        '- 输入与既有交付清单SHA-256匹配，绘图前后输入哈希不变；未调用LLM，未修改分类、主题或原主统计。',
        '- 303个unit及CIK×FY均唯一；全部已验证标签有通过QA的支持；无例外或不确定标签进入主题分子。',
        '- 全部15类频率、90个年度主题单元及105个主题对，与现有主表逐项一致；各年度组成精确加总100%。',
        '- 图中bar高度、stack分段、prevalence和disclosure rate均与导出绘图数据核对。所有图文字在画布内；PNG以300dpi导出，PDF保留矢量与嵌入字体。',
        '- 统一主题名、ID、颜色及legend顺序保存在 `theme_color_map.csv`；仅对长名称换行，未重命名、合并或省略主题。',
        '## 可复现与文件',
        '项目入口：`scripts/60_plot_governance_purpose_inductive.py`；复用既有 navy/deep-blue、DejaVu Sans、白底、弱网格、去除上/右边框的风格。此目录提供完整独立脚本 `plot_governance_purposes.py`。',
        '在项目环境运行：`.venv/Scripts/python.exe scripts/60_plot_governance_purpose_inductive.py`。也可直接运行本目录的 `plot_governance_purposes.py`；项目根目录由祖先路径发现，路径不依赖具体用户机器。',
        '绘图数据：`plot_theme_frequency.csv`、`plot_annual_metrics.csv`、`plot_annual_status.csv`、`plot_cooccurrence.csv`。这些是图形来源表，不是新的分类数据。',
        '验证和复现元数据：`visualization_qa.json`、`visualization_manifest.json`。Bundled Python缺少Matplotlib，实际使用项目既有`.venv`中的Matplotlib与NumPy，未安装或修改依赖。']
    blocks=[line for line in lines if line];content=''
    for i,block in enumerate(blocks):
        continuous=i and ((block.startswith('|') and blocks[i-1].startswith('|')) or
                          (block.startswith('- ') and blocks[i-1].startswith('- ')))
        content+=('' if i==0 else ('\n' if continuous else '\n\n'))+block
    (out/'visualization_report.md').write_text(content+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',default=RUN);p.add_argument('--output-dir',type=Path,default=DEFAULT_OUT)
    a=p.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    d=load_data(a.run_id)
    csvout(out/'plot_theme_frequency.csv',[dict(theme_id=t,theme_name=d['themes'][t],firm_year_count=d['freq'][t],denominator=d['n'],prevalence=d['freq'][t]/d['n']) for t in d['order']])
    csvout(out/'plot_annual_metrics.csv',d['metrics'])
    csvout(out/'plot_annual_status.csv',[{k:v for k,v in x.items() if k!='counts'} for x in d['annual']])
    csvout(out/'plot_cooccurrence.csv',[dict(theme_a=x,theme_b=y,firm_year_count=d['co'][x,y],reference_denominator=d['n']) for x in d['order'] for y in d['order']])
    audits,colors=figures(d,out)
    check(all(sha(ROOT/p)==h for p,h in d['inputs'].items()),'Classification inputs changed during visualization')
    import matplotlib,numpy
    qa=dict(passed=True,llm_calls=0,input_artifacts_unchanged=True,classification_result_edits=0,
        positive_firm_years=d['n'],verified_explicit_firm_years=d['summary']['explicit_purpose_firm_years'],themes=len(d['themes']),
        total_theme_assignments=d['assignment_n'],multi_label_firm_years=d['multi_label_n'],
        master_frequency_cells_checked=len(d['themes']),master_annual_cells_checked=len(d['metrics']),
        master_cooccurrence_pairs_checked=len(d['themes'])*(len(d['themes'])-1)//2,
        no_unresolved_labels_counted=True,all_counted_labels_have_verified_support=True,all_annual_assignment_shares_sum_to_one=True,
        figure_checks=audits,input_sha256=d['inputs'])
    dump(out/'visualization_qa.json',qa);write_report(d,out,qa)
    target=out/'plot_governance_purposes.py'
    if Path(__file__).resolve()!=target.resolve():shutil.copyfile(Path(__file__),target)
    dump(out/'visualization_manifest.json',dict(run_id=a.run_id,visualization_id=out.name,generated_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version,matplotlib=matplotlib.__version__,numpy=numpy.__version__,style_reference='governance_content_reporting.py::figures / 01_practices_frequency',
        input_sha256=d['inputs'],artifacts=[dict(path=f.name,sha256=sha(f)) for f in sorted(out.glob('*')) if f.is_file() and f.name!='visualization_manifest.json']))
    print(json.dumps(dict(output=str(out),figures=len(audits),qa_passed=True,annual_status=d['annual']),ensure_ascii=False))

if __name__=='__main__':main()
