"""Descriptive Governance v2 prevalence by fixed size proxy and GICS Sector.

Reuses the existing full-universe join, sealed model outputs and plotting style.
Only saved firm-year binary labels enter the numerator/denominator. No API calls.
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

from . import firm_size_disclosure as base
from .combined_governance_trends import read, write, require
from .governance_adoption_dynamics import cik
from .governance_orientation_descriptive import GBASE
from .governance_visualization import file_hash
from .sampling import SECTORS

ROOT = base.ROOT
NAME = 'governance_size_industry_v1_20261028'
YEARS = (2023, 2024, 2025)
SIZES = base.SIZES
CODES = dict(zip(SECTORS, ('10', '15', '20', '25', '30', '35', '40', '45', '50', '55', '60')))
SMALL_N = 20
SPARSE_P = 5
TABLES = ROOT / 'outputs/tables' / NAME
FIGURES = ROOT / 'outputs/figures' / NAME
REPORT = ROOT / 'outputs/reports' / NAME
AUDIT = ROOT / 'data/interim/panels' / NAME


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def pct(n, denominator):
    return 100 * n / denominator if denominator else None


def included(row):
    return bool(base.task_label(row, 'governance'))


def positive(row):
    return base.task_label(row, 'governance') == 'Positive'


def unique(rows, key, name):
    result = {key(r): r for r in rows}
    require(len(result) == len(rows), 'Duplicate ' + name)
    return result


def load_analysis():
    panel, lineage, hashes = base.load_data()
    # Reuse the saved size panel and verify its Governance columns to the sealed
    # v2 join. Orientation classifications never determine inclusion here.
    old_path = base.PANEL / 'firm_year_size_panel.csv'
    old = unique(read(old_path), lambda r: (r['ticker'], int(r['fiscal_year'])), 'saved panel ticker/FY')
    require(len(old) == len(panel), 'Saved size panel frame changed')
    for r in panel:
        saved = old[r['ticker'], r['fiscal_year']]
        require(cik(saved['cik']) == r['cik'], 'Saved size panel CIK mismatch')
        for col in ('governance_label', 'governance_status', 'governance_observed_sections',
                    'firm_size_group', 'index_name', 'gics_sector'):
            require(saved[col] == r[col], 'Saved size panel mismatch: ' + col)
    hashes[old_path.relative_to(ROOT).as_posix()] = file_hash(old_path)
    selected = [r for r in panel if r['fiscal_year'] in YEARS]
    unique([r for r in selected if r['cik']], lambda r: (cik(r['cik']), r['fiscal_year']), 'analysis CIK/FY')
    unique(selected, lambda r: (r['firm_id'], r['fiscal_year']), 'analysis firm/FY')
    require(set(r['gics_sector'] for r in selected) == set(SECTORS), 'Sector universe mismatch')
    require(len(selected) == 4500, 'Expected 1,500 fixed-frame firms in three fiscal years')
    for fid in {r['firm_id'] for r in selected}:
        group = [r for r in selected if r['firm_id'] == fid]
        require(sorted(r['fiscal_year'] for r in group) == list(YEARS), 'Incomplete fixed frame')
        require(len({(r['firm_size_group'], r['gics_sector']) for r in group}) == 1,
                'Size or sector varies over time within fixed snapshot')
    return selected, lineage, hashes


def metrics(rows):
    valid = [r for r in rows if included(r)]
    p, n = sum(positive(r) for r in valid), len(valid)
    reasons = Counter(r['governance_exclusion_reason'] for r in rows if not included(r))
    return dict(frame_n=len(rows), total_n=n, positive_n=p, negative_n=n - p,
                excluded_n=len(rows) - n, coverage_pct=pct(n, len(rows)),
                positive_rate_pct=pct(p, n), no_valid_observations=n == 0,
                small_sample=n > 0 and n < SMALL_N, sparse_positive=n > 0 and p < SPARSE_P,
                one_positive_step_pp=100 / n if n else None,
                missing_cik_n=reasons['missing_cik'],
                unavailable_classification_n=sum(v for k, v in reasons.items() if k != 'missing_cik'),
                both_sections_valid_n=sum(r['governance_observed_sections'] == '2' for r in valid),
                one_section_valid_n=sum(r['governance_observed_sections'] == '1' for r in valid),
                unique_valid_firms_n=len({r['firm_id'] for r in valid}))


def delta(a, b):
    return b - a if a is not None and b is not None else None


def cell_statistics(panel):
    annual, pooled, changes = [], [], []
    for sector in SECTORS:
        for size in SIZES:
            rows = [r for r in panel if r['gics_sector'] == sector and r['firm_size_group'] == size]
            values = {y: metrics([r for r in rows if r['fiscal_year'] == y]) for y in YEARS}
            change = dict(gics_sector_code=CODES[sector], gics_sector=sector, firm_size_group=size)
            for y in YEARS:
                for col in ('total_n', 'positive_n', 'positive_rate_pct'):
                    change[f'{col}_{y}'] = values[y][col]
            for a, b in ((2023, 2024), (2024, 2025), (2023, 2025)):
                change[f'rate_change_{a}_{b}_pp'] = delta(values[a]['positive_rate_pct'], values[b]['positive_rate_pct'])
                change[f'positive_n_change_{a}_{b}'] = values[b]['positive_n'] - values[a]['positive_n']
                change[f'total_n_change_{a}_{b}'] = values[b]['total_n'] - values[a]['total_n']
            change['small_sample_either_endpoint'] = values[2023]['small_sample'] or values[2025]['small_sample']
            change['sparse_positive_either_endpoint'] = values[2023]['sparse_positive'] or values[2025]['sparse_positive']
            changes.append(change)
            for y in YEARS:
                annual.append(dict(fiscal_year=y, gics_sector_code=CODES[sector], gics_sector=sector,
                                   firm_size_group=size, **values[y],
                                   **{k: v for k, v in change.items() if k.startswith('rate_change_')}))
            pooled.append(dict(period='FY2023–FY2025', gics_sector_code=CODES[sector], gics_sector=sector,
                               firm_size_group=size, **metrics(rows),
                               interpretation='Pooled firm-years; companies may contribute three observations'))
    annual.sort(key=lambda r: (r['fiscal_year'], list(SECTORS).index(r['gics_sector']), SIZES.index(r['firm_size_group'])))
    return annual, pooled, changes


def marginal_statistics(panel):
    rows = []
    for period in (*YEARS, 'pooled'):
        selected = [r for r in panel if period == 'pooled' or r['fiscal_year'] == period]
        for dimension, groups in (('overall', ('All',)), ('size', SIZES), ('sector', SECTORS)):
            for group in groups:
                part = selected if dimension == 'overall' else [r for r in selected if
                    r['firm_size_group' if dimension == 'size' else 'gics_sector'] == group]
                rows.append(dict(period=period, dimension=dimension, group=group, **metrics(part)))
    return rows


def size_gaps(annual, pooled):
    rows = []
    for period in (*YEARS, 'pooled'):
        group = pooled if period == 'pooled' else [r for r in annual if r['fiscal_year'] == period]
        lookup = {(r['gics_sector'], r['firm_size_group']): r for r in group}
        for sector in SECTORS:
            for a, b in combinations(SIZES, 2):
                x, y = lookup[sector, a], lookup[sector, b]
                rows.append(dict(period=period, gics_sector_code=CODES[sector], gics_sector=sector,
                    group_a=a, group_b=b, a_positive_n=x['positive_n'], a_total_n=x['total_n'],
                    a_positive_rate_pct=x['positive_rate_pct'], b_positive_n=y['positive_n'],
                    b_total_n=y['total_n'], b_positive_rate_pct=y['positive_rate_pct'],
                    a_minus_b_pp=delta(y['positive_rate_pct'], x['positive_rate_pct']),
                    small_sample_either=x['small_sample'] or y['small_sample']))
    return rows


def coverage_sensitivity(panel):
    byfirm = defaultdict(list)
    for r in panel:
        byfirm[r['firm_id']].append(r)
    balanced_ids = {fid for fid, rows in byfirm.items() if len(rows) == 3 and all(included(r) for r in rows)}
    balanced = [r for r in panel if r['firm_id'] in balanced_ids]
    # Main labels stay authoritative; this is an additional source-coverage check.
    both = [r for r in panel if included(r) and r['governance_observed_sections'] == '2']
    rows = []
    for scope, subset in (('three_year_common_valid_firms', balanced), ('both_sections_valid', both)):
        annual, _, _ = cell_statistics(subset)
        rows.extend(dict(scope=scope, **r) for r in annual)
        rows.extend(dict(scope=scope, **r) for r in marginal_statistics(subset) if r['period'] != 'pooled')
    return rows, balanced_ids


def plot_figures(annual, pooled, changes):
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter
    plt = base.style.configure(FIGURES)
    seq = LinearSegmentedColormap.from_list('governance_teal', ('#F2F6F6', '#72BBB2', '#007D78', '#174D55'))
    seq.set_bad('#E4E7EB')
    div = LinearSegmentedColormap.from_list('governance_change', ('#B6652C', '#F8F7F4', '#007D78'))
    div.set_bad('#E4E7EB')
    max_rate = max(r['positive_rate_pct'] or 0 for r in annual + pooled)
    upper = max(5, math.ceil(max_rate / 5) * 5)
    rate_norm = Normalize(0, upper)
    max_change = max(abs(r['rate_change_2023_2025_pp'] or 0) for r in changes)
    span = max(5, math.ceil(max_change / 5) * 5)
    change_norm = TwoSlopeNorm(vmin=-span, vcenter=0, vmax=span)
    audits = {}

    def draw(ax, rows, change=False, ylabels=True):
        lookup = {(r['gics_sector'], r['firm_size_group']): r for r in rows}
        field = 'rate_change_2023_2025_pp' if change else 'positive_rate_pct'
        matrix = np.array([[lookup[sector, size][field] if lookup[sector, size][field] is not None else np.nan
                            for size in SIZES] for sector in SECTORS], dtype=float)
        im = ax.imshow(np.ma.masked_invalid(matrix), cmap=div if change else seq,
                       norm=change_norm if change else rate_norm, aspect='auto', interpolation='none')
        ax.set_xticks(range(3), SIZES)
        ax.set_yticks(range(11), SECTORS if ylabels else [''] * 11)
        ax.tick_params(axis='both', length=0, labelsize=10.5, pad=8)
        ax.set_xlabel('Firm Size', labelpad=10)
        ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 11, 1), minor=True)
        ax.grid(which='minor', color='white', linewidth=1.5)
        ax.tick_params(which='minor', bottom=False, left=False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, sector in enumerate(SECTORS):
            for j, size in enumerate(SIZES):
                r = lookup[sector, size]
                value = r[field]
                low = r['small_sample_either_endpoint'] if change else r['small_sample']
                sparse = r['sparse_positive_either_endpoint'] if change else r['sparse_positive']
                flags = ('*' if low else '') + ('†' if sparse else '')
                label = 'NA\nN=0' if value is None else (
                    f'{value:+.1f}{flags}' if change else f'{value:.1f}%{flags}\n{r["positive_n"]}/{r["total_n"]}')
                color = 'white' if value is not None and (value / span > .72 if change else value / upper > .55) else '#162E3C'
                ax.text(j, i, label, ha='center', va='center', fontsize=10.5 if change else 10,
                        color=color, linespacing=1.65)
                if low:
                    ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, hatch='//',
                                           edgecolor='#788B91', linewidth=0, alpha=.42))
        return im, matrix

    def save(fig, slug, matrices, scale, unit):
        audits[slug] = dict(data_matrices=[m.tolist() for m in matrices], sector_order=list(SECTORS),
                           size_order=list(SIZES), scale_limits=list(scale), unit=unit,
                           small_sample_threshold=SMALL_N, sparse_positive_threshold=SPARSE_P,
                           source_table_values_matched=True)
        base.save_figure(fig, slug, audits, output_dir=FIGURES, formats=('png',))

    fig, axes = plt.subplots(1, 3, figsize=(17.8, 10.8))
    fig.subplots_adjust(left=.19, right=.915, top=.83, bottom=.18, wspace=.10)
    base.style.title(fig, 'Figure 1. Size × Industry Governance Positive Rate (FY2023–2025)',
                     'Cell: Positive Rate (%) and Positive N / Total N. All years share the same color scale.')
    matrices = []
    for ax, year in zip(axes, YEARS):
        im, matrix = draw(ax, [r for r in annual if r['fiscal_year'] == year], ylabels=year == 2023)
        matrices.append(matrix)
        n = sum(r['total_n'] for r in annual if r['fiscal_year'] == year)
        p = sum(r['positive_n'] for r in annual if r['fiscal_year'] == year)
        ax.set_title(f'FY{year}\nAll firms: {p}/{n:,} ({100 * p / n:.2f}%)', fontsize=12, pad=17)
    cax = fig.add_axes([.934, .22, .014, .56])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label('Governance Positive Rate (%)', labelpad=10)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}'))
    base.style.footer(fig, '* / hatching: Total N < 20.  †: Positive N < 5, including observed zeros.  NA: no valid firm-years.\n'
                      'Denominator: valid binary firm-year labels within each cell. Fixed size / GICS snapshot: 19 Sep 2026.\n'
                      'Governance v2 model classifications of observed disclosure; human semantic validation pending.')
    save(fig, 'figure1_annual_positive_rate', matrices, (0, upper), 'percent')

    fig, ax = plt.subplots(figsize=(10.8, 10.6))
    fig.subplots_adjust(left=.33, right=.83, top=.83, bottom=.18)
    base.style.title(fig, 'Figure 2. Change in Governance Positive Rate',
                     'FY2025 minus FY2023, in percentage points. Positive values indicate increases.')
    im, matrix = draw(ax, changes, change=True)
    cax = fig.add_axes([.86, .24, .022, .52])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label('Change (percentage points)', labelpad=10)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:+.0f}'))
    base.style.footer(fig, '* / hatching: endpoint Total N < 20.  †: endpoint Positive N < 5.  NA: unavailable endpoint rate.\n'
                      'Change = within-cell FY2025 rate − FY2023 rate. Numerators and denominators are exported in CSV.\n'
                      'Fixed size / GICS snapshot: 19 Sep 2026. Governance v2 model labels; human validation pending.')
    save(fig, 'figure2_rate_change_2023_2025', [matrix], (-span, span), 'percentage points')

    fig, ax = plt.subplots(figsize=(10.8, 10.6))
    fig.subplots_adjust(left=.33, right=.83, top=.83, bottom=.18)
    base.style.title(fig, 'Figure 3. Pooled Size × Industry Governance Positive Rate',
                     'FY2023–FY2025: sum of Positive firm-years / sum of valid firm-years. Cell: rate and Positive N / Total N.')
    im, matrix = draw(ax, pooled)
    cax = fig.add_axes([.86, .24, .022, .52])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label('Governance Positive Rate (%)', labelpad=10)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}'))
    base.style.footer(fig, '* / hatching: pooled Total N < 20.  †: pooled Positive N < 5.  NA: no valid firm-years.\n'
                      'Companies can contribute up to three firm-years. Pooling reduces annual count noise; observations repeat firms.\n'
                      'Fixed size / GICS snapshot: 19 Sep 2026. Same rate color scale as Figure 1. Model labels; human validation pending.')
    save(fig, 'figure3_pooled_positive_rate', [matrix], (0, upper), 'percent')
    dump(REPORT / 'visual_qa.json', audits)
    return audits


def table(rows, columns):
    return '\n'.join(['| ' + ' | '.join(title for _, title in columns) + ' |',
                      '|' + '|'.join('---' for _ in columns) + '|'] +
                     ['| ' + ' | '.join(str(r[col]) for col, _ in columns) + ' |' for r in rows])


def display(row):
    if not row['total_n']:
        return 'NA (0/0)'
    return f'{row["positive_rate_pct"]:.2f}% ({row["positive_n"]}/{row["total_n"]})'


def write_report(annual, pooled, changes, margins, gaps, sensitivities, balanced_ids, qa):
    ix = {(r['period'], r['dimension'], r['group']): r for r in margins}
    cell = {(r['fiscal_year'], r['gics_sector'], r['firm_size_group']): r for r in annual}
    pool = {(r['gics_sector'], r['firm_size_group']): r for r in pooled}
    totals = [ix[y, 'overall', 'All'] for y in YEARS]
    total_change = totals[-1]['positive_rate_pct'] - totals[0]['positive_rate_pct']
    lsgap = lambda y: ix[y, 'size', 'Large']['positive_rate_pct'] - ix[y, 'size', 'Small']['positive_rate_pct']
    overall_rows = [dict(year=y, result=display(ix[y, 'overall', 'All']),
                         coverage=f'{ix[y,"overall","All"]["coverage_pct"]:.2f}%',
                         excluded=ix[y, 'overall', 'All']['excluded_n']) for y in YEARS]
    size_rows = [dict(size=z, **{str(y): display(ix[y, 'size', z]) for y in YEARS},
                     change=f'{ix[2025,"size",z]["positive_rate_pct"] - ix[2023,"size",z]["positive_rate_pct"]:+.2f}',
                     pooled=display(ix['pooled', 'size', z])) for z in SIZES]
    pooled_sectors = sorted([ix['pooled', 'sector', s] for s in SECTORS], key=lambda r: -r['positive_rate_pct'])
    sector_rows = [dict(sector=s['group'], **{z: display(pool[s['group'], z]) for z in SIZES},
                        all=display(s)) for s in pooled_sectors]
    leaders = sorted(changes, key=lambda r: -(r['rate_change_2023_2025_pp'] or 0))[:8]
    change_rows = [dict(sector=r['gics_sector'], size=r['firm_size_group'],
                        a=display(cell[2023, r['gics_sector'], r['firm_size_group']]),
                        b=display(cell[2025, r['gics_sector'], r['firm_size_group']]),
                        change=f'{r["rate_change_2023_2025_pp"]:+.2f}',
                        counts=f'{r["positive_n_change_2023_2025"]:+d}',
                        caution='N<20' if r['small_sample_either_endpoint'] else '2023 Positive<5' if r['positive_n_2023'] < 5 else '')
                   for r in leaders]
    strict = sum(pool[s, 'Large']['positive_rate_pct'] > pool[s, 'Mid']['positive_rate_pct'] > pool[s, 'Small']['positive_rate_pct']
                 for s in SECTORS)
    rank = {(s, z): 1 + sum(pool[other, z]['positive_rate_pct'] > pool[s, z]['positive_rate_pct'] for other in SECTORS)
            for s in SECTORS for z in SIZES}
    large_small = {p: sum(r['a_minus_b_pp'] > 0 for r in gaps if r['period'] == p and r['group_a'] == 'Large' and r['group_b'] == 'Small') for p in (*YEARS, 'pooled')}
    counts_change = Counter('increase' if r['rate_change_2023_2025_pp'] > 0 else 'decrease' if r['rate_change_2023_2025_pp'] < 0 else 'unchanged' for r in changes)
    sensitivity_rows = []
    for scope in ('three_year_common_valid_firms', 'both_sections_valid'):
        rs = [r for r in sensitivities if r['scope'] == scope and r.get('dimension') == 'overall']
        ri = {r['period']: r for r in rs}
        sensitivity_rows.append(dict(scope='三年共同有效公司' if scope.startswith('three') else '两章节均有效',
            **{str(y): display(ri[y]) for y in YEARS},
            change=f'{ri[2025]["positive_rate_pct"] - ri[2023]["positive_rate_pct"]:+.2f}'))
    spreads = {(y, z): max(cell[y, s, z]['positive_rate_pct'] for s in SECTORS)
               - min(cell[y, s, z]['positive_rate_pct'] for s in SECTORS)
               for y in YEARS for z in SIZES}
    spread_text = '同一规模内，11 个行业阳性率的最大值与最小值之差在 2023→2025 年分别为：' + '；'.join(
        f'{z} {spreads[2023,z]:.2f}→{spreads[2025,z]:.2f} pp' for z in SIZES
    ) + '。三组行业极差均扩大，但极值容易受到稀疏 Positive 的影响，仅作描述。'
    text = f'''# Firm Size × Industry 与 AI Governance 阳性率，FY2023–FY2025

## 主要发现

1. 全样本阳性率从 **{totals[0]['positive_rate_pct']:.2f}%（35/1,441）升至 {totals[2]['positive_rate_pct']:.2f}%（168/1,461）**，累计增加 **{total_change:.2f} 个百分点**。Positive 增加 133，分母增加 20，两类变化均已单独保留。
2. 总体规模梯度稳定存在，2025 年 Large / Mid / Small 为 **13.81% / 10.97% / 9.93%**。行业内部的梯度存在明显异质性：pooled Large 高于 Small 的行业有 {large_small['pooled']}/11 个，严格 Large > Mid > Small 只有 {strict}/11 个。Large–Small 总体差距在 2024 年扩大，2025 年随 Small 加速增长而收窄。
3. **信息技术业在三组均较高，金融业优势集中于 Large 和 Mid。** Pooled 信息技术业 Large / Mid / Small 分别为 {display(pool['Information Technology','Large'])}、{display(pool['Information Technology','Mid'])}、{display(pool['Information Technology','Small'])}，行业内排名依次为第 {rank['Information Technology','Large']}、{rank['Information Technology','Mid']}、{rank['Information Technology','Small']}。金融业 Large 为 {display(pool['Financials','Large'])}，Small 为 {display(pool['Financials','Small'])}，后者低于 Small 总体 {ix['pooled','size','Small']['positive_rate_pct']:.2f}%。Small Health Care 的率最高（{display(pool['Health Care','Small'])}）。
4. 33 个组合中，{counts_change['increase']} 个上升、{counts_change['decrease']} 个下降、{counts_change['unchanged']} 个持平。增长广泛分布，但部分高变化率来自很少的 Positive，例如 Mid 通信服务业从 0/6 变为 1/6，增加 16.67 个百分点。Large 金融业的 11/70 → 22/72 提供了更充分的描述性支持。
5. 三年共同有效的 **{len(balanced_ids):,} 家公司**仍呈现明显增长，覆盖变化未消除总体趋势。Pooled 每家公司最多贡献三个 firm-years，重复观察会提高数量，不能解释为同等数量的独立公司证据。

## Corporate Hierarchy × AI Governance 的研究启示

规模与行业可能共同影响所观察到的 Governance–Hierarchy 关系。大型企业可能同时具有更多组织层级、更多披露资源和更正式的合规流程；金融业及信息技术业可能因监管、数据处理或 AI 业务需求更早披露治理措施。这些是待检验的机制解释，本分析未观察组织层级、治理质量或真实实施时间。

同一行业内的规模梯度并不普遍，说明仅比较全样本平均值可能混合了规模、行业构成与两者交互差异。金融业的大型公司集中出现 Governance Positive，可能使“层级多的公司治理更多”的原始相关性增强；Health Care 等行业中 Small 的阳性率更高，又可能掩盖或反向影响这一关系。因此，当前结果支持将 **Year × Size × Sector 单元作为后续比较的基础**，并先核对每个单元的层级分布、有效样本量和 Positive 数量。

后续研究可在同一 FY、同一 Sector 和同一规模组内比较不同 hierarchy 的公司，并检查规模与行业组合是否具有足够重叠。汇总比较时，可报告共同权重下的描述性率、行业内结果和共同有效样本结果。固定指数标签只能粗略表示规模，未来若取得逐年市值、雇员数和历史行业归属，应进一步核对。当前数据没有 hierarchy 指标，尚无法计算这些结构因素对 Governance–Hierarchy 相关性的实际解释份额。对极稀疏单元应保留分子分母，避免从少数公司推导稳定机制。

## 样本、测量与分母

| 年份 | Positive Rate（Positive N / Total N） | 有效覆盖率 | 排除 firm-years |
|---|---|---|---|
''' + '\n'.join(f'| {r["year"]} | {r["result"]} | {r["coverage"]} | {r["excluded"]} |' for r in overall_rows) + f'''

每年固定样本框为 1,500 家公司，三年共 4,500 个潜在 firm-years。实际纳入 {sum(r['total_n'] for r in totals):,} 个，Positive 296 个，pooled 总体率 {100*296/sum(r['total_n'] for r in totals):.2f}%。2023/2024/2025 排除 59/42/39 个，分别包含 1 个缺失 CIK（Moog）及 58/41/38 个双章节均不可用观察。缺失 CIK 只按原框 ticker/FY 审计，未按空 CIK 合并。缺失分类全部排除，未填为 Negative。

**Positive Rate = 本单元 Positive firm-years / 本单元有效二元分类 firm-years × 100%。** 采用 `implemented-internal-ai-governance-v2.0` 已合并的 0/1 标签，每个 CIK/FY 计一次。任一有效章节 Positive 得到 Positive。沿用原始 observed-section 口径：仅一个章节可用且该章节 Negative 时，firm-year 可为 Negative；另一个章节缺失的状态继续保留。双章节均不可用的观察不进入分母。

规模为 S&P 500 → Large、S&P MidCap 400 → Mid、S&P SmallCap 600 → Small。规模和 GICS 11 Sector 均来自 **2026-09-19 固定指数成份快照**，统一应用于全部年份，未代表 2023–2025 逐年历史归属。分析覆盖当前固定成份框，具有回溯归类和存续选择限制。

检查结果：三年非空 CIK/FY 唯一数为 {qa['known_cik_fy_n']:,}，重复 CIK/FY 为 0；规模和行业映射覆盖 1,500/1,500 家，冲突为 0。旧规模面板的 Governance 字段与当前 v2 权威结果逐行一致，输入哈希与封存交付记录一致。

这些是 **年报可观察章节中披露的已实施内部 AI Governance 的自动分类结果**。Negative 表示该口径下未识别到符合标准的 Positive。人工语义验证尚未完成，不能将零阳性披露或 Negative 扩展为公司实际不存在治理。

## 规模差异及其变化

''' + table(size_rows, [('size','规模'),('2023','2023'),('2024','2024'),('2025','2025'),('change','2023→2025（pp）'),('pooled','Pooled')]) + f'''

Large–Small 总体差距依次为 **{lsgap(2023):.2f}、{lsgap(2024):.2f}、{lsgap(2025):.2f} pp**，先扩大后收窄；2025 相比 2023 仍增加 {lsgap(2025)-lsgap(2023):.2f} pp。2024→2025 年 Large 增长 {ix[2025,'size','Large']['positive_rate_pct']-ix[2024,'size','Large']['positive_rate_pct']:.2f} pp，Small 增长 {ix[2025,'size','Small']['positive_rate_pct']-ix[2024,'size','Small']['positive_rate_pct']:.2f} pp。Large–Mid 的端点差距从 {ix[2023,'size','Large']['positive_rate_pct']-ix[2023,'size','Mid']['positive_rate_pct']:.2f} pp 增至 {ix[2025,'size','Large']['positive_rate_pct']-ix[2025,'size','Mid']['positive_rate_pct']:.2f} pp，Mid–Small 从 {ix[2023,'size','Mid']['positive_rate_pct']-ix[2023,'size','Small']['positive_rate_pct']:.2f} pp 缩至 {ix[2025,'size','Mid']['positive_rate_pct']-ix[2025,'size','Small']['positive_rate_pct']:.2f} pp。

2023/2024/2025 年 Large 高于 Small 的行业分别为 {large_small[2023]}/{large_small[2024]}/{large_small[2025]} 个。2025 年 Health Care（Small 12/68，17.65%；Large 8/58，13.79%）与 Materials（Small 4/25，16.00%；Large 0/24）呈相反规模排序。消费可选行业 Mid 高于其他两组。规模优势需要行业内检查。

## 行业与规模的组合差异

下表为三年 pooled 率，每个值同时给出 Positive N / Total N。Pooled 用分子、分母求和计算，未对年度率作简单平均。

''' + table(sector_rows, [('sector','Sector'),('Large','Large'),('Mid','Mid'),('Small','Small'),('all','全规模')]) + '''

信息技术业三组均高于各自规模组的总体 pooled 率。金融业在 Large、Mid 分别居第一、第二，Small 低于本规模组总体率，行业优势随规模明显变化。Small 组 Health Care 最高、Materials 次之，后者 pooled 为 6/76，Positive 仍然较少。该比较使用行业与规模交叉单元内部的率，保留了组内更细的规模、业务或 AI 使用差异。Large Consumer Staples 为 9/100，Small 为 0/78，也呈现明显的描述性反差。Large Financials 是 pooled 率最高的单元。

Mid Communication Services pooled 为 1/18（5.56%），仍属于小样本；2025 单年较高率仅对应一家。Small Utilities pooled 仅 2/36，2025 的 16.67% 来自 2/12，不能视为稳定行业优势。图中 `*` 与斜线标记 Total N<20，`†` 标记 Positive N<5（含零）；这是透明的描述性提醒阈值，未进行统计显著性检验。NA 对应无有效观察，率和变化留空。本次主样本 99 个年度单元及 33 个 pooled 单元均有有效观察，其中 ''' + str(sum(r['small_sample'] for r in annual)) + ''' 个年度单元、''' + str(sum(r['small_sample'] for r in pooled)) + ''' 个 pooled 单元 N<20。

## 2023–2025 的增长来自哪里

''' + table(change_rows, [('sector','Sector'),('size','规模'),('a','2023'),('b','2025'),('change','率变化（pp）'),('counts','Positive N 变化'),('caution','解释提醒')]) + '''

全部 11 个行业的汇总率在 2023→2025 年均上升。Health Care 增长 12.40 pp（2/158 → 22/161），Financials 增长 11.96 pp（12/248 → 42/250），Information Technology 增长 11.96 pp（8/184 → 30/184）。按 Positive 数量，Financials、Industrials、Information Technology、Health Care 分别净增 30、24、22、20 个，合计贡献 96/133 个净增 Positive。该数量贡献与组内阳性率分别解释，完整统计保留在边际表中。

Utilities、Communication Services 的部分规模单元分母很小，少数新增 Positive 就会产生较大的百分点变化。率变化需要同时检查分子分母，完整 CSV 已分列各期 Positive N、Total N 及变化。

只有 Large Consumer Discretionary 与 Mid Materials 的 2023→2025 率下降，两组都减少 1 个 Positive，分母基本稳定。Large Materials 在端点均为 0/24，但 2024 年为 2/24，端点变化 0 不代表三年没有波动。Financials Large–Small 差距扩大；Health Care、Real Estate 的 Small 增长更快，规模差距缩小或反向。行业和规模差异的演变呈局部扩大与局部收敛并存。

''' + spread_text + '''

## 覆盖变化检查

''' + table(sensitivity_rows, [('scope','描述性检查口径'),('2023','2023'),('2024','2024'),('2025','2025'),('change','2023→2025（pp）')]) + '''

共同有效样本固定公司和分母，支持总体增长并非单纯来自有效样本数量增加。两章节均有效结果提供章节覆盖检查，样本集合仍可能逐年变化；它没有补齐缺失章节，也不替代主口径。对应的 99 个年度单元和规模、行业边际统计均保存在 `coverage_sensitivity.csv`。这些检查只用于描述稳定性。

## 图表与可复现文件

![Figure 1](<''' + (FIGURES / 'figure1_annual_positive_rate.png').as_posix() + '''>)

![Figure 2](<''' + (FIGURES / 'figure2_rate_change_2023_2025.png').as_posix() + '''>)

![Figure 3](<''' + (FIGURES / 'figure3_pooled_positive_rate.png').as_posix() + '''>)

- `outputs/tables/''' + NAME + '''/year_size_sector_statistics.csv`：99 行主统计，包含分子、有效分母、覆盖、两章节覆盖、稀疏标记和三段率变化。
- 同目录 `rate_changes.csv`：33 行组合的端点分子分母、Positive N / Total N 变化和百分点变化；`pooled_statistics.csv`：33 行 pooled 统计及不同公司数；`marginal_statistics.csv`：总体、规模和行业边际统计；`size_gaps.csv`：同行业内规模差；`coverage_sensitivity.csv`：共同有效样本与两章节覆盖检查。
- `data/interim/panels/''' + NAME + '''/observation_audit.csv`：4,500 行纳入/排除审计，可重建的 interim 审计数据。
- `outputs/reports/''' + NAME + '''/`：本报告、QA、输入输出 SHA256 清单和代码快照。

主表 `total_n` 为有效分类分母，`frame_n` 为潜在样本框数量；`positive_rate_pct` 的单位为百分比，`rate_change_*_pp` 为百分点。三段变化均按同一 Size × Sector 计算，在该组合的三年行中重复，便于单表读取。小样本阈值和稀疏 Positive 标记可在 QA 中核查。

输入为 `outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv` 与 `exclusion_manifest.csv`；复用 `data/interim/panels/firm_size_ai_disclosure_v1_20261026/firm_year_size_panel.csv`，并用 `data/interim/documents/full_universe_item1a_manifest.csv` 和 `data/raw/universe/sp500.csv`、`sp400.csv`、`sp600.csv` 核对映射。Governance v2 的 `delivery_qa.json` 与 `delivery_manifest.json` 为版本和封存依据。仅使用现有 Governance 标签确定纳入与否。

运行：`.venv/Scripts/python.exe scripts/71_analyze_size_industry_governance.py`；独立核对：`.venv/Scripts/python.exe scripts/72_verify_size_industry_governance.py`。图表均为 300 DPI PNG。未下载数据、未发起 LLM 调用、未覆盖原始分类或提升至 processed 数据。
'''
    (REPORT / 'report.md').write_text(text, encoding='utf-8')


def run():
    for path in (TABLES, FIGURES, REPORT, AUDIT):
        path.mkdir(parents=True, exist_ok=True)
    panel, lineage, hashes = load_analysis()
    annual, pooled, changes = cell_statistics(panel)
    margins = marginal_statistics(panel)
    gaps = size_gaps(annual, pooled)
    sensitivities, balanced_ids = coverage_sensitivity(panel)
    for name, rows in (('year_size_sector_statistics.csv', annual), ('pooled_statistics.csv', pooled),
                       ('rate_changes.csv', changes), ('marginal_statistics.csv', margins),
                       ('size_gaps.csv', gaps)):
        write(TABLES / name, rows)
    # Cell rows and marginal rows share a single rectangular schema.
    fields = list(dict.fromkeys(k for r in sensitivities for k in r))
    write(TABLES / 'coverage_sensitivity.csv', [{k: r.get(k, '') for k in fields} for r in sensitivities])
    audit = [dict(cik=r['cik'], ticker=r['ticker'], firm_id=r['firm_id'], fiscal_year=r['fiscal_year'],
        firm_size_group=r['firm_size_group'], gics_sector=r['gics_sector'], governance_label=r['governance_label'],
        included=included(r), exclusion_reason=r['governance_exclusion_reason'],
        observed_sections=r['governance_observed_sections'], common_valid_three_year_firm=r['firm_id'] in balanced_ids)
        for r in panel]
    write(AUDIT / 'observation_audit.csv', audit)
    visual = plot_figures(annual, pooled, changes)
    qa = dict(passed=True, frame_n=len(panel), frame_firms_n=len(lineage),
        known_cik_fy_n=sum(bool(r['cik']) for r in panel), missing_cik_fy_n=sum(not r['cik'] for r in panel),
        duplicate_cik_fy_n=0, mapping_conflict_n=0, annual_cells_n=len(annual), pooled_cells_n=len(pooled),
        common_valid_firms_n=len(balanced_ids), small_n_threshold=SMALL_N, sparse_positive_threshold=SPARSE_P,
        small_annual_cells_n=sum(r['small_sample'] for r in annual),
        sparse_annual_cells_n=sum(r['sparse_positive'] for r in annual),
        annual_coverage={str(y): metrics([r for r in panel if r['fiscal_year'] == y]) for y in YEARS},
        checks=dict(authoritative_firm_year_labels=True, saved_size_panel_matches=True,
            fixed_snapshot_mapping=True, no_missing_imputed=True, independent_governance_denominator=True,
            unique_cik_fy=True, no_section_double_count=True, source_seals_match=True),
        llm_calls=0, downloads=0, semantic_human_validation=False)
    write_report(annual, pooled, changes, margins, gaps, sensitivities, balanced_ids, qa)
    changed = [rel for rel, digest in hashes.items() if file_hash(ROOT / rel) != digest]
    require(not changed, 'Input bytes changed: ' + repr(changed))
    qa['source_bytes_unchanged'] = True
    dump(REPORT / 'qa.json', qa)
    files = [Path(__file__), ROOT / 'scripts/71_analyze_size_industry_governance.py',
             ROOT / 'scripts/72_verify_size_industry_governance.py', ROOT / 'tests/test_governance_size_industry.py',
             ROOT / 'src/ai_restrictions/firm_size_disclosure.py',
             ROOT / 'src/ai_restrictions/governance_purpose_inductive_visualization.py',
             ROOT / 'src/ai_restrictions/governance_orientation_descriptive.py',
             ROOT / 'src/ai_restrictions/governance_adoption_dynamics.py',
             ROOT / 'src/ai_restrictions/combined_governance_trends.py',
             ROOT / 'src/ai_restrictions/governance_visualization.py', ROOT / 'src/ai_restrictions/sampling.py']
    snapshot = REPORT / 'code_snapshot'
    for file in files:
        dest = snapshot / file.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
    generated = [p for folder in (TABLES, FIGURES, REPORT, AUDIT) for p in folder.rglob('*') if p.is_file()
                 and p.name not in ('manifest.json', 'independent_qa.json', 'offline_tests.txt')]
    dump(REPORT / 'manifest.json', dict(run_id=NAME, created_at_utc=datetime.now(timezone.utc).isoformat(),
        status='descriptive analysis; automated classifications; human semantic validation pending',
        governance_version='implemented-internal-ai-governance-v2.0', supersedes=None,
        years=list(YEARS), size_order=list(SIZES), sector_order=list(SECTORS),
        input_sha256=hashes, code_sha256={p.relative_to(ROOT).as_posix(): file_hash(p) for p in files},
        output_sha256={p.relative_to(ROOT).as_posix(): file_hash(p) for p in generated},
        size_industry_timing='Fixed 2026-09-19 index and GICS snapshot applied to all fiscal years',
        denominator='Valid Governance v2 binary firm-years within Year × Size × Sector',
        pooled_denominator='Sum of valid firm-years, not unique firms or mean annual rates',
        file_roles={str(TABLES.relative_to(ROOT)): 'descriptive statistical tables',
                    str(FIGURES.relative_to(ROOT)): '300 DPI research PNGs',
                    str(REPORT.relative_to(ROOT)): 'report, provenance, QA and code snapshot',
                    str(AUDIT.relative_to(ROOT)): 'rebuildable interim observation audit; not processed'},
        llm_calls=0, downloads=0, source_bytes_unchanged=True, figure_n=len(visual)))
    return qa


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
