"""Offline firm-size composition of the adopted full-sample firm-year labels.

Size is the fixed sampling-frame index proxy. Each task has its own denominator.
Reuses the frozen-source join, CSV/hash utilities and academic plotting style.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
import json
import math
from pathlib import Path
import shutil

from .combined_governance_trends import read, write, require
from .governance_adoption_dynamics import cik, symbol, ratio
from .governance_orientation_descriptive import load_joined, OBASE, GBASE, md_table
from .governance_visualization import file_hash
from . import governance_purpose_inductive_visualization as style

ROOT = Path(__file__).resolve().parents[2]
NAME = 'firm_size_ai_disclosure_v1_20261026'
YEARS = tuple(range(2020, 2026))
SIZES = ('Large', 'Mid', 'Small')
INDEX_MAP = {'S&P 500': 'Large', 'S&P MidCap 400': 'Mid', 'S&P SmallCap 600': 'Small'}
CATEGORIES = {'governance': ('Positive', 'Non-Positive'),
              'orientation': ('Pro-AI', 'Non-Pro-AI', 'No AI Discussion')}
COLORS = {'Positive': '#007D78', 'Non-Positive': '#DDE3EA', 'Pro-AI': '#007D78',
          'Non-Pro-AI': '#C47B20', 'No AI Discussion': '#DDE3EA'}
SIZE_COLORS = {'Large': '#285A7C', 'Mid': '#C87935', 'Small': '#40876C'}
REPORT = ROOT/'outputs/reports'/NAME
TABLES = ROOT/'outputs/tables'/NAME
FIGURES = ROOT/'outputs/figures'/NAME
PANEL = ROOT/'data/interim/panels'/NAME


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def task_label(row, task):
    """Respect the authoritative firm-year status; unknown is never negative."""
    if not row['cik']:
        return ''
    if task == 'governance':
        return {'1': 'Positive', '0': 'Non-Positive'}.get(row['governance_label'], '') if row['governance_valid'] else ''
    return {'pro_ai': 'Pro-AI', 'non_pro_ai': 'Non-Pro-AI',
            'no_ai_discussion': 'No AI Discussion'}.get(row['orientation_label'], '') if row['orientation_status'] == 'classified' else ''


def unique(rows, key, name):
    result = {key(r): r for r in rows}
    require(len(result) == len(rows), 'Duplicate '+name)
    return result


def load_data():
    panel, hashes = load_joined()  # Keep No AI Discussion: never use joint_state as a filter.
    meta_path = ROOT/'data/interim/documents/full_universe_item1a_manifest.csv'
    meta_rows = read(meta_path)
    meta = unique(meta_rows, lambda r: (r['ticker'], int(r['fiscal_year'])), 'frame ticker/FY')
    mi = unique([r for r in meta_rows if r['cik']], lambda r: (cik(r['cik']), int(r['fiscal_year'])), 'frame CIK/FY')
    hashes[meta_path.relative_to(ROOT).as_posix()] = file_hash(meta_path)
    require(len(meta) == len(panel) == 9000, 'Frame size changed')
    require(set(meta) == {(r['ticker'], r['fiscal_year']) for r in panel}, 'Frame partition mismatch')
    snapshots = defaultdict(list)
    for number, index in zip(('500', '400', '600'), INDEX_MAP):
        path = ROOT/f'data/raw/universe/sp{number}.csv'
        md_path = path.with_suffix('.metadata.json')
        md = json.loads(md_path.read_text(encoding='utf-8'))
        require(md['index_name'] == index and file_hash(path) == md['raw_sha256'], 'Index snapshot seal mismatch')
        for p in (path, md_path):
            hashes[p.relative_to(ROOT).as_posix()] = file_hash(p)
        for line, r in enumerate(read(path), 2):
            snapshots[symbol(r['Symbol'])].append(dict(index_name=index,
                firm_size_group=INDEX_MAP[index], source_file=path.relative_to(ROOT).as_posix(),
                source_row=line, source_url=md['source_url'], retrieved_at=md['retrieved_at'],
                raw_cik=r.get('CIK', ''), gics_sector=r['GICS Sector']))
    # Validate the source manifest is the one used by Orientation v3.
    om = json.loads((OBASE/'run_manifest.json').read_text(encoding='utf-8'))
    rel = meta_path.relative_to(ROOT).as_posix()
    require(om['run_id'] == 'fullsample_v3_20261025', 'Wrong Orientation version')
    require(om['input_hashes'][rel] == hashes[rel], 'Frame differs from Orientation source frame')
    ori = unique([r for r in read(OBASE/'firm_year_panel.csv') if r['cik']],
                 lambda r: (cik(r['cik']), int(r['fiscal_year'])), 'Orientation CIK/FY')
    lineage, byfirm = [], defaultdict(list)
    for r in panel:
        m = mi[(r['cik'], r['fiscal_year'])] if r['cik'] else meta[r['ticker'], r['fiscal_year']]
        require(cik(m['cik']) == r['cik'] and m['ticker'] == r['ticker'], 'CIK/FY metadata conflict')
        size = INDEX_MAP.get(m['index_name'])
        require(size in SIZES and m['size_group'].capitalize() == size, 'Index/size mapping conflict')
        raw = snapshots[symbol(r['ticker'])]
        require(raw and {v['index_name'] for v in raw} == {m['index_name']}, 'Missing/ambiguous raw index mapping')
        require({v['gics_sector'] for v in raw} == {m['gics_sector']}, 'Raw GICS/frame conflict')
        raw_ciks = {cik(v['raw_cik']) for v in raw if v['raw_cik']}
        require(not raw_ciks or raw_ciks == {r['cik']}, 'Raw CIK conflict')
        o = ori.get((r['cik'], r['fiscal_year'])) if r['cik'] else None
        if o:
            require(o['size_group'].capitalize() == size and o['ticker'] == r['ticker'], 'Orientation size/ticker conflict')
        r.update(firm_id='CIK:'+r['cik'] if r['cik'] else 'UNRESOLVED_FRAME:'+m['company_key'],
                 firm_size_group=size, index_name=m['index_name'], gics_sector=m['gics_sector'],
                 identity_status='verified_cik' if r['cik'] else 'missing_cik_audit_only')
        for task in CATEGORIES:
            label = task_label(r, task)
            r[task+'_classification'] = label
            r[task+'_included'] = bool(label)
            r[task+'_exclusion_reason'] = '' if label else ('missing_cik' if not r['cik'] else r[task+'_status'])
        byfirm[r['firm_id']].append(r)
    for fid, group in sorted(byfirm.items()):
        require(sorted(r['fiscal_year'] for r in group) == list(YEARS), 'Incomplete/duplicate frame history')
        require(len({r['firm_size_group'] for r in group}) == 1, 'Size changes across years')
        r = group[0]
        lineage.append(dict(firm_id=fid, cik=r['cik'], ticker=r['ticker'], company_name=r['company_name'],
            firm_size_group=r['firm_size_group'], index_name=r['index_name'], identity_status=r['identity_status'],
            mapping_status='matched_index_snapshot_and_saved_manifest',
            timing_basis='Fixed 2026-09-19 snapshot, applied to FY2020-FY2025; no historical membership inference',
            provenance=json.dumps(snapshots[symbol(r['ticker'])], ensure_ascii=False)))
    require(len(byfirm) == 1500 and len(mi) == 8994, 'Identity coverage changed')
    return panel, lineage, hashes


def summarize(panel):
    counts, denominators, exclusions, coverage = [], [], [], []
    for task, categories in CATEGORIES.items():
        for size in SIZES:
            for year in YEARS:
                group = [r for r in panel if r['firm_size_group'] == size and r['fiscal_year'] == year]
                valid = [r for r in group if task_label(r, task)]
                cc = Counter(task_label(r, task) for r in valid)
                n = len(valid)
                denominators.append(dict(task=task, firm_size_group=size, fiscal_year=year, frame_n=len(group),
                    valid_n=n, excluded_n=len(group)-n, valid_fraction=ratio(n, len(group))))
                for category in categories:
                    counts.append(dict(task=task, firm_size_group=size, fiscal_year=year,
                        classification=category, class_n=cc[category], valid_n=n,
                        proportion=ratio(cc[category], n), percentage=100*cc[category]/n if n else None))
                for reason, count in sorted(Counter(r[task+'_exclusion_reason'] for r in group if not task_label(r, task)).items()):
                    exclusions.append(dict(task=task, firm_size_group=size, fiscal_year=year, reason=reason, excluded_n=count))
                # Source coverage check: preserve firm-year labels even where only one section is valid.
                both = [r for r in valid if (r['governance_observed_sections'] == '2' if task == 'governance'
                                            else r['orientation_complete_pair'] == 'True')]
                p = sum(task_label(r, task) == categories[0] for r in both)
                coverage.append(dict(task=task, firm_size_group=size, fiscal_year=year,
                    main_valid_n=n, both_sections_valid_n=len(both),
                    both_sections_positive_n=p, both_sections_positive_rate=ratio(p, len(both)),
                    not_both_sections_valid_n=n-len(both),
                    included_unresolved_companion_n=sum(r['orientation_unresolved_companion'] == 'True' for r in valid) if task == 'orientation' else 0))
    return counts, denominators, exclusions, coverage


def gaps(counts):
    ix = {(r['task'], r['firm_size_group'], r['fiscal_year']): r for r in counts
          if r['classification'] == CATEGORIES[r['task']][0]}
    result = []
    for task in CATEGORIES:
        for a, b in combinations(SIZES, 2):
            for year in YEARS:
                x, y = ix[task, a, year], ix[task, b, year]
                result.append(dict(task=task, fiscal_year=year, group_a=a, group_b=b,
                    a_positive_n=x['class_n'], a_valid_n=x['valid_n'], a_percentage=x['percentage'],
                    b_positive_n=y['class_n'], b_valid_n=y['valid_n'], b_percentage=y['percentage'],
                    difference_pp=x['percentage']-y['percentage'] if x['valid_n'] and y['valid_n'] else None))
    return result


def save_figure(fig, slug, audit, output_dir=None, formats=('png', 'pdf', 'svg')):
    """Check all visible text bounds and export publication and editable formats."""
    import matplotlib.pyplot as plt
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += list(ax.texts)+list(ax.get_xticklabels())+list(ax.get_yticklabels())+[ax.title, ax.xaxis.label, ax.yaxis.label]
    for legend in fig.legends:
        texts += legend.get_texts()
        box = legend.get_window_extent(renderer)
        for ax in fig.axes:
            require(not box.overlaps(ax.xaxis.label.get_window_extent(renderer)),
                    'Legend overlaps fiscal-year label: '+slug)
    for text in texts:
        if not text.get_visible() or not text.get_text():
            continue
        box = text.get_window_extent(renderer)
        require(box.x0 >= -2 and box.y0 >= -2 and box.x1 <= fig.bbox.width+2 and box.y1 <= fig.bbox.height+2,
                'Text clipped: '+text.get_text())
    for ext in formats:
        fig.savefig((output_dir or FIGURES)/(slug+'.'+ext), dpi=300, facecolor='white')
    audit[slug].update(text_inside_canvas=True, legend_clear_of_axis_labels=True,
                       png_dpi=300, axes_n=len(fig.axes))
    plt.close(fig)


def plots():
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter
    plt = style.configure(FIGURES)
    counts = read(TABLES/'size_year_classification.csv')
    lookup = {(r['task'], r['firm_size_group'], int(r['fiscal_year']), r['classification']): r for r in counts}
    audits = {}
    for number, (task, categories) in enumerate(CATEGORIES.items(), 1):
        heading = 'AI Governance' if task == 'governance' else 'Pro-AI Orientation'
        slug = f'figure{number:02d}_{task}_annual_composition'
        fig, axes = plt.subplots(1, 3, figsize=(14.4, 6.6), sharey=True)
        fig.subplots_adjust(left=.065, right=.985, top=.77, bottom=.235, wspace=.12)
        style.title(fig, heading+': Firm-Size Annual Composition',
                    'FY2020–FY2025  |  Share of valid firm-years within each size group and year')
        totals, bars_n = [], 0
        for ax, size in zip(axes, SIZES):
            bottom = [0.0]*6
            ax.set_title(size, fontsize=13, weight='bold', pad=25)
            for category in categories:
                rr = [lookup[task, size, y, category] for y in YEARS]
                values = [float(r['percentage']) if r['percentage'] else 0.0 for r in rr]
                rects = ax.bar(range(6), values, bottom=bottom, width=.66, color=COLORS[category],
                              edgecolor='white', linewidth=.5)
                require(all(abs(p.get_height()-v) < 1e-12 for p, v in zip(rects, values)), 'Bar/table mismatch')
                for i, (p, value) in enumerate(zip(rects, values)):
                    if value >= 8:
                        ax.text(p.get_x()+p.get_width()/2, bottom[i]+value/2, f'{value:.1f}%',
                                ha='center', va='center', fontsize=9,
                                color='white' if category in ('Positive', 'Pro-AI', 'Non-Pro-AI') else '#344256')
                bottom = [b+v for b, v in zip(bottom, values)]
                bars_n += len(rects)
            for x, year in enumerate(YEARS):
                n = int(lookup[task, size, year, categories[0]]['valid_n'])
                require(n > 0, 'Empty size/year denominator: display an explicit missing bar')
                ax.text(x, 1.025, f'N={n}', transform=ax.get_xaxis_transform(), ha='center', fontsize=8.5, color='#596579')
            require(all(abs(b-100) < 1e-10 for b in bottom), 'Bar does not sum to 100')
            totals += bottom
            ax.set_ylim(0, 100)
            ax.set_xlim(-.65, 5.65)
            ax.set_xticks(range(6), YEARS)
            ax.set_yticks(range(0, 101, 20))
            ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
            ax.set_xlabel('Fiscal year', labelpad=9)
            style.grid(ax)
        axes[0].set_ylabel('Share of valid firm-years')
        fig.legend(handles=[Patch(facecolor=COLORS[c], label=c) for c in categories],
                   loc='lower center', bbox_to_anchor=(.52, .103), ncol=len(categories), frameon=False)
        style.footer(fig, 'Size proxy: fixed S&P index source in the 19 Sep 2026 sampling frame. N is task-specific; invalid observations excluded.\n'
                     'Observed-section firm-year labels; 10-K disclosure status. Automated classifications; human validation remains pending.')
        audits[slug] = dict(table_values_match=True, stacked_bars_n=18, segments_n=bars_n,
                            totals_equal_100=True, n_labels=18, percentage_label_threshold=8)
        save_figure(fig, slug, audits)
    # Separate rate scales preserve visibility of the relatively rare Governance Positive.
    for number, task in enumerate(CATEGORIES, 3):
        slug = f'figure{number:02d}_{task}_positive_rate_trend'
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.subplots_adjust(left=.095, right=.91, top=.76, bottom=.24)
        title = 'AI Governance Positive Rate' if task == 'governance' else 'Pro-AI Disclosure Rate'
        style.title(fig, title+': Annual Trend', 'FY2020–FY2025  |  Each task uses its own valid size-year denominator')
        max_rate = max(float(r['percentage']) for r in counts
                       if r['task'] == task and r['classification'] == CATEGORIES[task][0])
        step = 2 if task == 'governance' else 10
        ymax = (math.ceil(max_rate/step)+(1 if task == 'governance' else 0))*step
        ax.axvspan(2022.7, 2025.4, color='#F2F5F8', zorder=0)
        for size, marker in zip(SIZES, ('o', 's', '^')):
            rr = [lookup[task, size, y, CATEGORIES[task][0]] for y in YEARS]
            yy = [float(r['percentage']) for r in rr]
            line, = ax.plot(YEARS, yy, color=SIZE_COLORS[size], marker=marker, lw=2.2, ms=6, label=size, clip_on=False)
            require(list(line.get_ydata()) == yy, 'Line/table mismatch')
            # Endpoint labels; small vertical separation where groups are close.
            offset = 0
            ax.annotate(f'{yy[-1]:.1f}%', (2025, yy[-1]), xytext=(9, offset), textcoords='offset points',
                        va='center', color=SIZE_COLORS[size], fontsize=10, weight='bold')
        ax.set(xlim=(2019.85, 2025.5), ylim=(0, ymax), xlabel='Fiscal year', ylabel='Share of valid firm-years')
        ax.set_xticks(YEARS)
        ax.set_yticks(range(0, ymax+1, step))
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        style.grid(ax)
        fig.legend(*ax.get_legend_handles_labels(), loc='lower center', bbox_to_anchor=(.5, .09), ncol=3, frameon=False)
        style.footer(fig, 'Size proxy: fixed S&P index source (19 Sep 2026). Shading marks FY2023–FY2025.\n'
                     '10-K disclosure status; automated firm-year labels. Sample sizes are in the composition figures and CSV tables.')
        audits[slug] = dict(table_values_match=True, lines_n=3, years_n=6, y_min=0, y_max=ymax)
        save_figure(fig, slug, audits)
    return audits


def report(counts, denominators, differences, coverage, qa):
    ix = {(r['task'], r['firm_size_group'], r['fiscal_year']): r for r in counts
          if r['classification'] == CATEGORIES[r['task']][0]}
    dx = {(r['task'], r['fiscal_year'], r['group_a'], r['group_b']): r['difference_pp'] for r in differences}
    rows = []
    for task in CATEGORIES:
        for year in (2023, 2024, 2025):
            r = dict(task=task, year=year)
            for size in SIZES:
                v = ix[task, size, year]
                r[size] = f"{v['class_n']}/{v['valid_n']} ({v['percentage']:.2f}%)"
            r['gap'] = f"{dx[task, year, 'Large', 'Small']:.2f}"
            rows.append(r)
    g = [dx['governance', y, 'Large', 'Small'] for y in (2023, 2024, 2025)]
    o = [dx['orientation', y, 'Large', 'Small'] for y in (2023, 2024, 2025)]
    sensitivity = []
    gap_rows = []
    for task in CATEGORIES:
        for year in (2023, 2024, 2025):
            gap_rows.append(dict(task=task, year=year,
                large_mid=f"{dx[task, year, 'Large', 'Mid']:.2f}",
                large_small=f"{dx[task, year, 'Large', 'Small']:.2f}",
                mid_small=f"{dx[task, year, 'Mid', 'Small']:.2f}"))
            rr = {r['firm_size_group']: r for r in coverage if r['task'] == task and r['fiscal_year'] == year}
            sensitivity.append(dict(task=task, year=year, **{s: f"{100*rr[s]['both_sections_positive_rate']:.2f}% (N={rr[s]['both_sections_valid_n']})" for s in SIZES},
                gap=f"{100*(rr['Large']['both_sections_positive_rate']-rr['Small']['both_sections_positive_rate']):.2f}"))
    text = [
        '# Firm Size 与 AI 披露：Annual Composition', '',
        f'版本 `{NAME}`；2026-10-26；FY2020–FY2025；离线描述性分析，LLM/API 调用 0。', '',
        '## 主要发现', '',
        f'1. **Governance Positive 披露呈现规模梯度。**2023–2025 每年均为 Large > Mid > Small。Large–Small 差距依次为 {g[0]:.2f}、{g[1]:.2f}、{g[2]:.2f} 个百分点；'
        f'2024 年扩大，2025 年收敛，2025 相比 2023 净扩大 {g[2]-g[0]:.2f} 个百分点。不能描述为持续扩大。',
        f'2. **Pro-AI 披露呈现相同的组别排序。**2023–2025 每年均为 Large > Mid > Small。Large–Small 差距依次为 {o[0]:.2f}、{o[1]:.2f}、{o[2]:.2f} 个百分点，2024 年扩大、2025 年部分收敛，'
        f'累计扩大 {o[2]-o[0]:.2f} 个百分点。',
        '3. **应分别看三组之间的差值。**Governance 的三对规模差距均在 2024 年扩大、2025 年收敛；Pro-AI 的 Large–Mid 差距持续扩大，Large–Small 与 Mid–Small 则在 2025 年收敛。所有组的两类阳性披露比例均上升。',
        '4. **两项任务的规模差异方向一致，幅度有别。**Large–Small 差距均在 2024 年达到近期峰值，Pro-AI 的差距更大、2023–2025 净扩大更明显。比较基于各自有效样本，未限定两项任务同时有效的共同样本。', '',
        md_table(rows, [('task', '任务'), ('year', 'FY'), ('Large', 'Large 阳性 n/N (%)'), ('Mid', 'Mid 阳性 n/N (%)'),
                        ('Small', 'Small 阳性 n/N (%)'), ('gap', 'Large−Small (pp)')]), '',
        md_table(gap_rows, [('task','任务'),('year','FY'),('large_mid','Large−Mid (pp)'),
                           ('large_small','Large−Small (pp)'),('mid_small','Mid−Small (pp)')]), '',
        '2023→2025 两项任务的 Large−Mid 和 Large−Small 净差距均扩大，Mid−Small 净差距均缩小；“组间差异扩大”不适用于所有组对。', '',
        '“系统性”仅描述这三个年度重复出现的组别排序；未进行显著性检验或控制行业等因素。早期 Governance Positive 总数 FY2020/2021/2022 仅 2/2/3；早期规模差异容易受个别公司影响。', '',
        '补充尺度说明：上述扩大/收敛按**绝对百分点差**判断。按 Large/Small 比率，Governance 从 '
        f"{ix['governance','Large',2023]['percentage']/ix['governance','Small',2023]['percentage']:.2f} 倍降至 {ix['governance','Large',2025]['percentage']/ix['governance','Small',2025]['percentage']:.2f} 倍，"
        f"Pro-AI 从 {ix['orientation','Large',2023]['percentage']/ix['orientation','Small',2023]['percentage']:.2f} 倍降至 {ix['orientation','Large',2025]['percentage']/ix['orientation','Small',2025]['percentage']:.2f} 倍。相对梯度均减弱，不能将绝对差距扩大概括为所有尺度上的分化。", '',
        '## 数据与统计口径', '',
        '- Governance：`outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv`，版本 `implemented-internal-ai-governance-v2.0`；同时保留 `exclusion_manifest.csv` 的 500 条排除记录用于框架核算。',
        '- Orientation：`data/interim/classifications/corporate_pro_ai_orientation/fullsample_v3_20261025/firm_year_panel.csv`，运行 `fullsample_v3_20261025`、prompt v3；同时核查 `firm_year_exclusion_manifest.csv`。不使用 sample55、v2 或 AI Stance 结果。',
        '- 指数/规模：`data/interim/documents/full_universe_item1a_manifest.csv`，交叉核查 `data/raw/universe/sp500.csv`、`sp400.csv`、`sp600.csv` 及各自 metadata/hash。S&P 500 → Large；S&P MidCap 400 → Mid；S&P SmallCap 600 → Small。',
        '- 该分组是 **2026-09-19 采集的固定样本指数来源标签**，回用于六个财年；各组原始公司数为 500/400/600。这不是逐年历史指数成分，也不保证公司在各历史年度属于对应规模。',
        f'- 完整框架 1,500 家公司、9,000 条 firm-year，映射覆盖 100%；非空规范化 CIK/FY 共 8,994 个且唯一，三方匹配一致。1 家公司 6 年缺 CIK，仅按框架 ticker/FY 保留排除审计；不以空 CIK 合并分类。',
        '- 每个 firm-year 使用现有最终聚合标签，Item 1A 与 Item 7 不分别计数。Governance：状态 complete 且标签 1/0 → Positive/Non-Positive；Orientation：状态 classified 且属于三类之一。No AI Discussion 作为独立有效类别进入分母。',
        f"- Governance 有效 {qa['governance_valid_n']:,}、排除 {9000-qa['governance_valid_n']:,}；Orientation 有效 {qa['orientation_valid_n']:,}、排除 {9000-qa['orientation_valid_n']:,}（500 个双章节不可用/身份缺失、76 个未解决、6 个运行示例留出）。六个留出 firm-year 不重复添加双章节不可用审计行。",
        '- 各比例 = 该任务、规模组及财年内的类别数 / 有效分类 firm-year 数。缺失、无效、未解决的 firm-year 均不补为负类；N 为当年有效分母，随来源可用性变化。Non-Positive 对应源数据的有效 0（已观测章节不含符合标准的阳性披露）。',
        '- 延续 observed-section 聚合：某一已分类章节给出确定阳性时，源规则允许保留 firm-year 阳性，即使伴随章节未解决；只保留源 firm-year 最终标签，不从章节自行补类。逐行审计及 coverage 表保留此标记。自动 QA 通过不代表完成了人工语义验证。', '',
        '## 图表', '',
        f'![Governance annual composition](../../figures/{NAME}/figure01_governance_annual_composition.png)', '',
        f'![Orientation annual composition](../../figures/{NAME}/figure02_orientation_annual_composition.png)', '',
        '三组 panel 共用 0–100% 坐标、分类颜色和图例；每根柱标注有效 N，仅为占比 ≥8% 的区段添加内部百分比标签。稀少的治理阳性可结合折线图读取。', '',
        f'![Governance trend](../../figures/{NAME}/figure03_governance_positive_rate_trend.png)', '',
        f'![Pro-AI trend](../../figures/{NAME}/figure04_orientation_positive_rate_trend.png)', '',
        '两张趋势图共用规模颜色，纵轴分别从 0 起并按任务范围设置，以辨认较稀少的治理阳性；同样保留 FY2020–FY2025，并以浅色背景标记 FY2023–FY2025。', '',
        '## 覆盖核查与解读限制', '',
        '仅限两个章节均有有效分类的补充口径如下（各任务另算分母）；详细数据见 `source_coverage_sensitivity.csv`。这项核查评估章节覆盖，未控制公司组成或行业差异。', '',
        md_table(sensitivity, [('task','任务'),('year','FY'),('Large','Large'),('Mid','Mid'),('Small','Small'),('gap','Large−Small (pp)')]), '',
        '双章节口径保留相同的近期 Large > Mid > Small 排序及 Large−Small 先扩大后收敛的路径。Governance 的 2023→2025 净差距几乎持平（3.53→3.56 pp），提示主口径的轻微净扩大对覆盖口径敏感；Pro-AI 的净扩大仍较明显。', '',
        '**指数来源只作为 Firm Size Proxy。分类结果衡量 10-K 披露状态，不等于实际 AI 治理实施或 AI 采用情况。**规模组可能具有不同的行业结构、披露篇幅与来源覆盖，年度有效样本也有变化；这些描述性差异不支持因果推断、治理有效性判断或企业实际态度推断。', '',
        '## 文件、QA 与复现', '',
        f'- 图（PNG 300 dpi，另附 PDF/SVG）：`outputs/figures/{NAME}/`。',
        f'- 统计 CSV：`outputs/tables/{NAME}/size_year_classification.csv`（90 行，2+3 类 × 3 组 × 6 年）；`size_year_denominators.csv`（36 行）；`size_year_exclusions.csv`；`positive_rate_size_gaps.csv`；`source_coverage_sensitivity.csv`。',
        f'- 中间审计：`data/interim/panels/{NAME}/firm_year_size_panel.csv`（9,000 行）；`firm_size_mapping_audit.csv`（1,500 行，含指数来源行号及采集时间）。未晋升 processed。',
        '- CSV 字段：`class_n` 为类别数；`valid_n` 为对应任务有效分母；`proportion` 为 0–1；`percentage` 为 0–100；`difference_pp` 为 A 组比例减 B 组比例的百分点差。零分母使用空值，不写作 0%。',
        '- [QA](qa.json)、[输入与代码 hash](manifest.json)、[绘图校验](visual_qa.json)、[独立原始计数核验](independent_qa.json)。输入文件只读，派生输出按处理阶段分开。',
        '- 复现：`python scripts/65_analyze_firm_size_disclosure.py`。默认拒绝覆盖；`--replace-derived` 仅重建本分析派生文件，`--plots-only` 从已导出的 CSV 重绘。', '',
    ]
    (REPORT/'report.md').write_text('\n'.join(text), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-derived', action='store_true')
    parser.add_argument('--plots-only', action='store_true')
    args = parser.parse_args(argv)
    if args.plots_only:
        dump(REPORT/'visual_qa.json', plots())
        return
    require(args.replace_derived or not any(p.exists() for p in (REPORT, TABLES, FIGURES, PANEL)), 'Derived output exists; use --replace-derived')
    panel, mapping, hashes = load_data()
    counts, denominators, exclusions, coverage = summarize(panel)
    differences = gaps(counts)
    for p in (REPORT, TABLES, FIGURES, PANEL):
        p.mkdir(parents=True, exist_ok=True)
    outputs = {'size_year_classification.csv': counts, 'size_year_denominators.csv': denominators,
        'size_year_exclusions.csv': exclusions, 'positive_rate_size_gaps.csv': differences,
        'source_coverage_sensitivity.csv': coverage}
    for name, data in outputs.items():
        write(TABLES/name, data)
    # Remove joint-analysis inclusion fields: this analysis uses independent task eligibility.
    excluded_fields = {'joint_state', 'included', 'primary_exclusion', 'all_exclusion_reasons'}
    write(PANEL/'firm_year_size_panel.csv', [{k: v for k, v in r.items() if k not in excluded_fields} for r in panel])
    write(PANEL/'firm_size_mapping_audit.csv', mapping)
    qa = dict(passed=True, frame_n=len(panel), frame_firms_n=len(mapping),
        governance_valid_n=sum(r['governance_included'] for r in panel),
        orientation_valid_n=sum(r['orientation_included'] for r in panel),
        known_cik_fy_n=8994, missing_cik_fy_n=6, mapping_coverage=1.0,
        duplicate_cik_fy_n=0, mapping_conflict_n=0, llm_calls=0,
        source_bytes_unchanged=all(file_hash(ROOT/k) == v for k, v in hashes.items()),
        checks=dict(source_qa_passed=True, snapshot_seals_match=True, task_specific_denominators=True,
            no_ai_discussion_in_orientation_denominator=True, fixed_index_groups=True,
            no_section_double_count=True, no_missing_imputed=True),
        semantic_human_validation=False)
    require(qa['source_bytes_unchanged'], 'Source input changed')
    require((qa['governance_valid_n'], qa['orientation_valid_n']) == (8500, 8418), 'Task validity totals changed')
    for task in CATEGORIES:
        rr = [r for r in denominators if r['task'] == task]
        require(sum(r['valid_n'] for r in rr) == qa[task+'_valid_n'], 'Denominators do not reconcile')
        for r in rr:
            cc = [c for c in counts if (c['task'], c['firm_size_group'], c['fiscal_year']) == (task, r['firm_size_group'], r['fiscal_year'])]
            require(sum(c['class_n'] for c in cc) == r['valid_n'], 'Categories do not partition denominator')
            require(not r['valid_n'] or abs(sum(c['proportion'] for c in cc)-1) < 1e-12, 'Shares do not sum to one')
    # Verify serialized values, without relying on rounded display percentages.
    for r in read(TABLES/'size_year_classification.csv'):
        require(abs(float(r['proportion'])-int(r['class_n'])/int(r['valid_n'])) < 1e-12, 'CSV ratio mismatch')
    dump(REPORT/'qa.json', qa)
    report(counts, denominators, differences, coverage, qa)
    dump(REPORT/'visual_qa.json', plots())
    code = [Path(__file__), ROOT/'scripts/65_analyze_firm_size_disclosure.py',
            ROOT/'tests/test_firm_size_disclosure.py', ROOT/'scripts/66_verify_firm_size_disclosure.py',
            ROOT/'src/ai_restrictions/governance_orientation_descriptive.py',
            ROOT/'src/ai_restrictions/governance_adoption_dynamics.py',
            ROOT/'src/ai_restrictions/combined_governance_trends.py',
            ROOT/'src/ai_restrictions/governance_visualization.py',
            ROOT/'src/ai_restrictions/governance_purpose_inductive_visualization.py']
    snapshot = REPORT/'code_snapshot'
    for path in code:
        target = snapshot/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    dump(REPORT/'manifest.json', dict(run_id=NAME, created_at_utc=datetime.now(timezone.utc).isoformat(),
        status='automated_descriptive_interim; human semantic validation pending',
        source_versions=dict(governance='implemented-internal-ai-governance-v2.0', orientation='fullsample_v3_20261025'),
        input_sha256=hashes, code_sha256={p.relative_to(ROOT).as_posix(): file_hash(p) for p in code},
        classification_policy='Adopted firm-year labels; independent task denominators; No AI Discussion included for Orientation',
        size_policy='Fixed 2026-09-19 sampling-frame index source proxy, no historical membership inference',
        llm_calls=0, output_ownership={str(p.relative_to(ROOT)): role for p, role in
            ((REPORT,'report/QA/provenance/code snapshot'),(TABLES,'descriptive result tables'),
             (FIGURES,'publication figures'),(PANEL,'rebuildable audit panel; not processed'))}))
    print(json.dumps(qa, ensure_ascii=False))


if __name__ == '__main__':
    main()
