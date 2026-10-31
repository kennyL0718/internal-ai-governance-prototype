"""Size composition conditional on disclosure category, with annual category N.

Reuses the authoritative source join, fixed index mapping and plotting exporter.
No acquisition, classification, network call, or original-result writer is run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from . import firm_size_disclosure as base
from .combined_governance_trends import read, write, require
from .governance_orientation_descriptive import OBASE, GBASE, md_table
from .governance_visualization import file_hash

ROOT, YEARS, SIZES = base.ROOT, base.YEARS, base.SIZES
NAME = 'firm_size_within_disclosure_composition_v1_20261026'
REPORT = ROOT/'outputs/reports'/NAME
TABLES = ROOT/'outputs/tables'/NAME
FIGURES = ROOT/'outputs/figures'/NAME
TARGETS = {
    'governance_positive': ('governance', 'Positive'),
    'pro_ai': ('orientation', 'Pro-AI'),
    'non_pro_ai': ('orientation', 'Non-Pro-AI'),
}
EXTRA = {'no_ai_discussion': ('orientation', 'No AI Discussion')}
TITLES = {
    'governance_positive': 'Firm-Size Composition among Firms with Implemented AI Governance',
    'pro_ai': 'Firm-Size Composition among Pro-AI Firms',
    'non_pro_ai': 'Firm-Size Composition among Non-Pro-AI Firms',
}


def summarize_targets(panel, targets=None):
    """Condition on class first: denominator sums the three sizes in that class."""
    targets = TARGETS if targets is None else targets
    seen = set()
    for r in panel:
        if not r['cik']:
            require(not any(base.task_label(r, t) for t in ('governance', 'orientation')),
                    'Missing identity cannot carry an included classification')
            continue
        key = (base.cik(r['cik']), int(r['fiscal_year']))
        require(key not in seen, 'Duplicate normalized CIK/FY')
        seen.add(key)
        require(r['firm_size_group'] in SIZES, 'Unmapped size')
        require(int(r['fiscal_year']) in YEARS, 'Unexpected fiscal year')
    long, wide = [], []
    for target, (task, label) in targets.items():
        for year in YEARS:
            matched = [r for r in panel if int(r['fiscal_year']) == year and base.task_label(r, task) == label]
            cc = Counter(r['firm_size_group'] for r in matched)
            n = len(matched)
            require(sum(cc[s] for s in SIZES) == n, 'Category includes an unmapped size')
            summary = dict(fiscal_year=year, target_group=target, total_n=n)
            for size in SIZES:
                share = base.ratio(cc[size], n)
                long.append(dict(fiscal_year=year, target_group=target, firm_size_group=size,
                    count=cc[size], share_within_target_group=share, target_group_total_n=n))
                summary[size.lower()+'_n'] = cc[size]
            for size in SIZES:
                summary[size.lower()+'_share'] = base.ratio(cc[size], n)
            wide.append(summary)
    return long, wide


def plot_compositions():
    """Plot exported class-conditioned shares; fixed colors and identical axes."""
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter
    plt = base.style.configure(FIGURES)
    rows = read(TABLES/'target_group_size_composition_tidy.csv')
    lookup = {(r['target_group'], int(r['fiscal_year']), r['firm_size_group']): r for r in rows}
    audit = {}
    for number, target in enumerate(TARGETS, 1):
        slug = f'figure{number:02d}_{target}_firm_size_composition'
        fig, ax = plt.subplots(figsize=(12.8, 6.8))
        fig.subplots_adjust(left=.09, right=.975, top=.79, bottom=.25)
        base.style.title(fig, TITLES[target],
            'FY2020–FY2025  |  Denominator: all valid firms in the named disclosure category in each fiscal year')
        bottom = [0.0]*6
        ns = [int(lookup[target, year, 'Large']['target_group_total_n']) for year in YEARS]
        for size in SIZES:
            values = [100*float(lookup[target, year, size]['share_within_target_group']) if n else 0
                      for year, n in zip(YEARS, ns)]
            bars = ax.bar(range(6), values, bottom=bottom, width=.62,
                          color=base.SIZE_COLORS[size], edgecolor='white', linewidth=.7)
            require(all(abs(bar.get_height()-value) < 1e-12 for bar, value in zip(bars, values)), 'Plot/table disagreement')
            for i, value in enumerate(values):
                if value >= 5:
                    ax.text(i, bottom[i]+value/2, f'{value:.1f}%', ha='center', va='center',
                            color='white', fontsize=12)
            bottom = [a+b for a, b in zip(bottom, values)]
        for x, (year, n, total) in enumerate(zip(YEARS, ns, bottom)):
            require(abs(total-(100 if n else 0)) < 1e-10, 'Stack sum does not match category N')
            if not n:
                ax.text(x, 50, 'No valid\nobservations', ha='center', va='center', color='#596579')
            ax.text(x, 1.025, f'N={n:,}', transform=ax.get_xaxis_transform(), ha='center',
                    color='#596579', fontsize=10)
        ax.set(xlim=(-.65, 5.65), ylim=(0, 100), xlabel='Fiscal year',
               ylabel='Share within the annual disclosure category')
        ax.set_xticks(range(6), YEARS)
        ax.set_yticks(range(0, 101, 20))
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.xaxis.labelpad = 10
        base.style.grid(ax)
        fig.legend(handles=[Patch(facecolor=base.SIZE_COLORS[s], label=s) for s in SIZES],
                   loc='lower center', bbox_to_anchor=(.52, .115), ncol=3, frameon=False)
        note = ('FY2020–FY2022: only 2, 2 and 3 Governance Positive firm-years; interpret early composition cautiously.\n'
                if target == 'governance_positive' else
                'No AI Discussion, invalid/unresolved labels and runtime holdouts are excluded from this category.\n')
        base.style.footer(fig, note+
            'Size proxy: fixed S&P index source (19 Sep 2026). Composition of automated 10-K disclosure labels; human validation pending.')
        audit[slug] = dict(plotted_values_equal_csv=True, annual_bars_n=6, size_segments_n=18,
            nonempty_annual_stacks_sum_to_100=True, n_labels=ns, percentage_label_threshold=5,
            colors=base.SIZE_COLORS, share_denominator='annual named disclosure category total across sizes')
        base.save_figure(fig, slug, audit, output_dir=FIGURES, formats=('png', 'pdf'))
    return audit


def independently_verify(long, wide):
    """Recount raw final-label CSVs, bypassing the analysis join and task_label."""
    meta = read(ROOT/'data/interim/documents/full_universe_item1a_manifest.csv')
    mi = {}
    for r in meta:
        if not r['cik']:
            continue
        key = (r['cik'].zfill(10), int(r['fiscal_year']))
        require(key not in mi, 'Duplicate metadata CIK/FY')
        mi[key] = base.INDEX_MAP[r['index_name']]
    counts, totals = Counter(), Counter()
    sources = [('governance', read(GBASE/'combined_firm_year_v2_panel.csv')),
               ('orientation', read(OBASE/'firm_year_panel.csv'))]
    for task, source in sources:
        seen = set()
        for r in source:
            if not r['cik']:
                continue
            key = (r['cik'].zfill(10), int(r['fiscal_year']))
            require(key not in seen, 'Duplicate source CIK/FY')
            seen.add(key)
            if task == 'governance':
                target = 'governance_positive' if r['classification_status']=='complete' and r['implemented_internal_ai_governance_v2']=='1' else ''
            else:
                target = r['classification'] if r['classification_status']=='classified' else ''
                if target not in ('pro_ai', 'non_pro_ai', 'no_ai_discussion'):
                    target = ''
            if target:
                counts[target, key[1], mi[key]] += 1
                totals[target, key[1]] += 1
    for r in long:
        key = r['target_group'], r['fiscal_year'], r['firm_size_group']
        n = totals[key[:2]]
        require(r['count'] == counts[key] and r['target_group_total_n'] == n, 'Independent count mismatch')
        require(r['share_within_target_group'] == base.ratio(counts[key], n), 'Independent share mismatch')
    require(len(long) == len(wide)*3, 'Long/wide row count mismatch')
    for r in wide:
        require(r['total_n'] == totals[r['target_group'], r['fiscal_year']], 'Wide denominator mismatch')
        for size in SIZES:
            require(r[size.lower()+'_n'] == counts[r['target_group'], r['fiscal_year'], size], 'Wide count mismatch')
            require(r[size.lower()+'_share'] == base.ratio(r[size.lower()+'_n'], r['total_n']), 'Wide share mismatch')
    return dict(passed=True, independent_raw_source_count_check=True,
                checked_long_rows=len(long), checked_wide_rows=len(wide),
                category_totals={t: sum(v for (g, y), v in totals.items() if g == t) for t in (*TARGETS, *EXTRA)})


def summary_markdown(wide):
    rows = [dict(year=r['fiscal_year'], target=r['target_group'], n=r['total_n'],
                 **{s: f"{r[s.lower()+'_n']} ({100*r[s.lower()+'_share']:.2f}%)" if r['total_n'] else 'NA' for s in SIZES}) for r in wide]
    return md_table(rows, [('year','FY'),('target','Target group'),('n','N'),('Large','Large n (%)'),
                           ('Mid','Mid n (%)'),('Small','Small n (%)')])


def write_report(wide, qa):
    ix = {(r['target_group'], r['fiscal_year']): r for r in wide}
    def pct(t, y, s='large'):
        return 100*ix[t, y][s+'_share']
    recent = [r for r in wide if r['fiscal_year'] >= 2023]
    text = ['# 披露类别内部的年度 Firm-Size Composition', '',
        f'运行 `{NAME}`；2026-10-26；FY2020–FY2025。完全离线，LLM/API 调用 0。', '',
        '## 描述性发现', '',
        '1. **Governance Positive 内部的规模构成逐步分散。**FY2020–FY2022 的 Large 均为 100%，但每年 N 仅 2、2、3。'
        f"FY2023–FY2025 的 Large 为 {pct('governance_positive',2023):.2f}%→{pct('governance_positive',2024):.2f}%→{pct('governance_positive',2025):.2f}%；"
        f"Small 从 {pct('governance_positive',2023,'small'):.2f}% 升至 {pct('governance_positive',2025,'small'):.2f}%，Mid 约为 26%。Large 仍为最大组，2025 年已低于半数。",
        '2. **Pro-AI 内部 Large 在六个年度都是占比最高的单一规模组。**'
        f"其占比从 FY2020 的 {pct('pro_ai',2020):.2f}% 变为 FY2023 的 {pct('pro_ai',2023):.2f}% 和 FY2025 的 {pct('pro_ai',2025):.2f}%。"
        f"FY2025 的 Mid/Small 分别为 {pct('pro_ai',2025,'mid'):.2f}%/{pct('pro_ai',2025,'small'):.2f}%。除 FY2020 外，Large 均未过半。",
        '3. **Non-Pro-AI 的近期构成更偏向 Small。**'
        f"FY2023 的 Large/Small 为 {pct('non_pro_ai',2023):.2f}%/{pct('non_pro_ai',2023,'small'):.2f}%；"
        f"FY2025 为 {pct('non_pro_ai',2025):.2f}%/{pct('non_pro_ai',2025,'small'):.2f}%。Small 在 FY2024 和 FY2025 成为最大组。"
        f"FY2025 Pro-AI 的 Large 占比较 Non-Pro-AI 高 {pct('pro_ai',2025)-pct('non_pro_ai',2025):.2f} 个百分点。",
        '4. **FY2023–FY2025 三个类别均未出现 Large 占比上升。**'
        'Large 在 Governance Positive、Pro-AI、Non-Pro-AI 中分别下降 '
        + '、'.join(f"{pct(t,2023)-pct(t,2025):.2f}" for t in TARGETS)+' 个百分点。'
        'Large 对应的类别计数可以上升，同时类别总数增长更快，导致其内部份额下降。',
        '5. **Governance Positive 对 Large 的集中程度随年份改变。**'
        f"FY2023 Governance Positive 与 Pro-AI 的 Large 占比分别为 {pct('governance_positive',2023):.2f}%/{pct('pro_ai',2023):.2f}%，"
        f"FY2024 为 {pct('governance_positive',2024):.2f}%/{pct('pro_ai',2024):.2f}%；"
        f"FY2025 转为 {pct('governance_positive',2025):.2f}%/{pct('pro_ai',2025):.2f}%。"
        'FY2025 两类的三组构成较接近，Governance Positive 的 Large 份额略低；“Governance 始终更偏向大公司”缺乏支持。', '',
        summary_markdown(recent), '',
        '## 图表', '',
    ]
    for number, target in enumerate(TARGETS, 1):
        slug = f'figure{number:02d}_{target}_firm_size_composition'
        text += [f'![{TITLES[target]}](../../figures/{NAME}/{slug}.png)', '',
                 f'[PDF](../../figures/{NAME}/{slug}.pdf)', '']
    text += ['## 口径与限制', '',
        '- 固定当年目标类别，分母为该类别内 Large + Mid + Small 的有效 firm-year 总数；每年三种规模份额之和为 100%。N 是当年的目标类别总数。三个类别分别计算，无需两项任务同时有效。',
        '- Governance 采用 firm-year 最终 complete/1 标签；Orientation 采用 firm-year 最终 classified/pro_ai 或 non_pro_ai 标签。缺失、无效、未解决和运行示例留出不进入目标类别；No AI Discussion 仅在独立附表统计。',
        '- 沿用源 observed-section 聚合：若已分类章节确定阳性，伴随章节未解决时仍可有有效的最终 Pro-AI firm-year 标签；完整未解决的 firm-year 不计入。分类在自动 QA 范围内有效，人工语义验证仍待完成。',
        '- 每家公司每财年最多计一次，Item 1A/Item 7 通过已采用的 firm-year 最终标签聚合。复用最新全样本 Governance v2.0 与 Orientation fullsample_v3_20261025，未拼接旧版或样本运行标签。',
        '- S&P 500 → Large；S&P MidCap 400 → Mid；S&P SmallCap 600 → Small。该映射来自 **2026-09-19 固定样本指数快照**，仅为 Firm Size Proxy，不代表 FY2020–FY2025 每年的历史指数成分或实际市值。',
        '- 原始框架 1,500 家（Large/Mid/Small = 500/400/600）×6 年。指数映射覆盖 100%；8,994 个非空 CIK/FY 唯一，另 1 家公司 6 年缺 CIK，仅保留框架排除审计。框架组别数量不相等，图中构成受到样本设计和分类覆盖影响。',
        '- 本图估计的是 `P(size | disclosure category, year)`；“某规模组出现该披露类别的比例”对应另一条件概率。类别内份额下降可以与该规模组内部的披露率上升同时发生。',
        '- **图展示披露分类结果内部的规模构成，不等于真实 AI 治理或 AI 采用的总体分布。**不做因果推断，不据此判断实际实施、治理有效性、企业真实态度或历史采用时点。', '',
        '## 数据、输出与复现', '',
        '- Governance：`outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv`（v2.0），同目录排除清单用于框架完整性核查。',
        '- Orientation：`data/interim/classifications/corporate_pro_ai_orientation/fullsample_v3_20261025/firm_year_panel.csv` 及排除清单（prompt v3）。',
        '- 规模及身份：`data/interim/documents/full_universe_item1a_manifest.csv`，与 `data/raw/universe/sp500.csv`、`sp400.csv`、`sp600.csv` 及 metadata/hash 交叉核查；复用 `firm_size_disclosure.load_data()`，不重复保存同一中间面板。',
        f'- 核心图（各 PNG 300 dpi + PDF）：`outputs/figures/{NAME}/`。三图统一 Large/Mid/Small 配色、图例顺序及 0–100% 纵轴。',
        f'- 表：`outputs/tables/{NAME}/target_group_size_composition_tidy.csv`（54 行）；`target_group_size_composition_summary.csv`（18 行）；`target_group_size_composition_summary.md`；另附 `no_ai_discussion_size_composition_tidy.csv` 与 `no_ai_discussion_size_composition_summary.csv`。',
        '- `share_within_target_group`、`large_share`、`mid_share`、`small_share` 均为 0–1；无类别观察的年份占比为空值。所有计数及分母均保留整数。',
        f"- QA：独立从原始最终分类回算 {qa['checked_long_rows']} 行长表、{qa['checked_wide_rows']} 行宽表（含 No AI Discussion），与分析聚合一致；[qa.json](qa.json)、[visual_qa.json](visual_qa.json)、[manifest.json](manifest.json) 记录校验与来源。",
        '- 复现：`python scripts/67_analyze_size_within_disclosure.py`。默认拒绝覆盖；`--replace-derived` 仅重建本分析派生输出；`--plots-only` 从统计 CSV 重绘。既有分类及上一轮图表均保留。', '',
    ]
    (REPORT/'report.md').write_text('\n'.join(text), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-derived', action='store_true')
    parser.add_argument('--plots-only', action='store_true')
    args = parser.parse_args(argv)
    if args.plots_only:
        base.dump(REPORT/'visual_qa.json', plot_compositions())
        return
    require(args.replace_derived or not any(p.exists() for p in (REPORT, TABLES, FIGURES)),
            'Derived output exists; use --replace-derived')
    panel, mapping, hashes = base.load_data()
    long, wide = summarize_targets(panel)
    extra_long, extra_wide = summarize_targets(panel, EXTRA)
    qa = independently_verify(long+extra_long, wide+extra_wide)
    for path in (REPORT, TABLES, FIGURES):
        path.mkdir(parents=True, exist_ok=True)
    data = {'target_group_size_composition_tidy.csv':long,
            'target_group_size_composition_summary.csv':wide,
            'no_ai_discussion_size_composition_tidy.csv':extra_long,
            'no_ai_discussion_size_composition_summary.csv':extra_wide}
    for filename, rows in data.items():
        write(TABLES/filename, rows)
    for filename in ('target_group_size_composition_tidy.csv', 'no_ai_discussion_size_composition_tidy.csv'):
        for r in read(TABLES/filename):
            require(abs(float(r['share_within_target_group'])-int(r['count'])/int(r['target_group_total_n'])) < 1e-12,
                    'Serialized share mismatch')
    (TABLES/'target_group_size_composition_summary.md').write_text(summary_markdown(wide)+'\n', encoding='utf-8')
    qa.update(frame_n=len(panel), frame_firms_n=len(mapping), nonempty_cik_fy_n=8994, missing_cik_fy_n=6,
        duplicate_cik_fy_n=0, index_mapping_coverage=1.0, llm_calls=0,
        source_versions=dict(governance='implemented-internal-ai-governance-v2.0', orientation='fullsample_v3_20261025'),
        core_tidy_rows=len(long), core_summary_rows=len(wide),
        denominator='Within fiscal_year and target_group, sum of Large/Mid/Small count',
        no_section_double_count=True, no_invalid_labels_imputed=True, human_semantic_validation=False)
    write_report(wide, qa)
    base.dump(REPORT/'visual_qa.json', plot_compositions())
    qa['input_sha256_unchanged'] = all(file_hash(ROOT/k) == v for k,v in hashes.items())
    require(qa['input_sha256_unchanged'], 'Source bytes changed')
    base.dump(REPORT/'qa.json', qa)
    code = [Path(__file__), ROOT/'scripts/67_analyze_size_within_disclosure.py',
            ROOT/'tests/test_firm_size_target_composition.py',
            ROOT/'src/ai_restrictions/firm_size_disclosure.py',
            ROOT/'src/ai_restrictions/governance_orientation_descriptive.py',
            ROOT/'src/ai_restrictions/governance_adoption_dynamics.py',
            ROOT/'src/ai_restrictions/combined_governance_trends.py',
            ROOT/'src/ai_restrictions/governance_visualization.py',
            ROOT/'src/ai_restrictions/governance_purpose_inductive_visualization.py']
    for path in code:
        dest = REPORT/'code_snapshot'/path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    base.dump(REPORT/'manifest.json', dict(run_id=NAME, created_at_utc=datetime.now(timezone.utc).isoformat(),
        status='descriptive model-label composition; human semantic review pending', source_versions=qa['source_versions'],
        input_sha256=hashes, code_sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in code},
        denominator=qa['denominator'], llm_calls=0,
        output_ownership={p.relative_to(ROOT).as_posix():role for p,role in
            ((FIGURES,'final PNG/PDF research figures'),(TABLES,'research summary tables'),
             (REPORT,'report, QA, provenance, code snapshot; no new intermediate panel'))}))
    print(json.dumps(qa, ensure_ascii=False))


if __name__ == '__main__':
    main()
