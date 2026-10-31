"""Industry composition of adopted full-sample firm-year disclosure labels.

Reuse the frozen-source firm-size join and figure style. Company GICS labels
are the saved 2026-09-19 snapshot; no acquisition or reclassification is run.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from . import firm_size_disclosure as base
from .combined_governance_trends import read, write, require
from .governance_orientation_descriptive import GBASE, OBASE
from .governance_visualization import file_hash
from .sampling import SECTORS as SECTOR_NAMES

ROOT = base.ROOT
NAME = 'industry_within_disclosure_composition_v1_20261028'
OUT = ROOT / 'outputs/figures' / NAME
YEARS = (2023, 2024, 2025)
CODE_SOURCE = 'https://www.spglobal.com/spdji/en/landing/topic/gics/'
# Canonical name-to-code translation only; companies keep their existing labels.
SECTORS = dict(zip(('10', '15', '20', '25', '30', '35', '40', '45', '50', '55', '60'), SECTOR_NAMES))
COLORS = dict(zip(SECTORS, (
    '#8F5E47', '#B6A268', '#40876C', '#C87935', '#B7BD75', '#8175A5',
    '#285A7C', '#3E9BA5', '#C66D86', '#6C7B91', '#A8998E',
)))
TARGETS = {'governance_positive': ('governance', 'Positive'), 'pro_ai': ('orientation', 'Pro-AI')}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fraction(n, denominator):
    return n / denominator if denominator else None


def percent(n, denominator):
    return 100 * n / denominator if denominator else None


def load_analysis():
    panel, lineage, hashes = base.load_data()
    report_dir = ROOT / 'outputs/reports/fullsample_v3_20261025'
    seal_path = report_dir / 'delivery_manifest.json'
    seal = json.loads(seal_path.read_text(encoding='utf-8'))
    require(seal['run_id'] == 'fullsample_v3_20261025' and seal['qa_passed'], 'Wrong/failed Orientation delivery')
    for path in (OBASE / 'firm_year_panel.csv', OBASE / 'firm_year_exclusion_manifest.csv', OBASE / 'run_manifest.json'):
        rel = path.relative_to(ROOT).as_posix()
        require(file_hash(path) == seal['files'][rel]['sha256'], 'Orientation sealed artifact changed: ' + rel)
    for path in (seal_path, report_dir / 'independent_delivery_qa.json'):
        hashes[path.relative_to(ROOT).as_posix()] = file_hash(path)
    require(json.loads((report_dir / 'independent_delivery_qa.json').read_text())['passed'], 'Orientation independent source QA failed')
    require(set(SECTORS.values()) == {r['gics_sector'] for r in panel}, 'Missing/unknown GICS Sector')
    by_firm = defaultdict(list)
    for r in panel:
        by_firm[r['firm_id']].append(r)
    require(all(len({r['gics_sector'] for r in rows}) == 1 for rows in by_firm.values()), 'Snapshot sector varies by fiscal year')
    sector_by_key = {(r['cik'], r['fiscal_year']): r['gics_sector'] for r in panel if r['cik']}
    orientation_rows = read(OBASE / 'firm_year_panel.csv')
    for r in orientation_rows:
        if r['cik']:
            require(r['gics_sector'] == sector_by_key[base.cik(r['cik']), int(r['fiscal_year'])], 'Orientation GICS/frame mismatch')
        require(r['run_id'] == 'fullsample_v3_20261025', 'Mixed Orientation run IDs')
    return panel, lineage, hashes


def summarize(panel):
    composition, rates, coverage = [], [], []
    for year in base.YEARS:
        year_rows = [r for r in panel if r['fiscal_year'] == year]
        for task, positive in TARGETS.values():
            valid = [r for r in year_rows if base.task_label(r, task)]
            labels = Counter(base.task_label(r, task) for r in valid)
            excluded = Counter(r[task + '_exclusion_reason'] for r in year_rows if not base.task_label(r, task))
            coverage.append(dict(
                fiscal_year=year, task=task, frame_n=len(year_rows), valid_n=len(valid),
                excluded_n=len(year_rows) - len(valid), valid_coverage_pct=percent(len(valid), len(year_rows)),
                positive_n=labels[positive], non_positive_n=len(valid) - labels[positive],
                no_ai_discussion_n=labels['No AI Discussion'] if task == 'orientation' else 0,
                missing_cik_n=excluded['missing_cik'], double_unavailable_n=excluded['excluded_double_unavailable'],
                unresolved_n=excluded['unresolved'], runtime_holdout_n=excluded['runtime_holdout'],
                both_sections_classified_n=sum(r['governance_observed_sections'] == '2' if task == 'governance'
                    else r['orientation_complete_pair'] == 'True' for r in valid),
                positive_with_unresolved_companion_n=sum(base.task_label(r, task) == positive and
                    r['orientation_unresolved_companion'] == 'True' for r in valid) if task == 'orientation' else 0,
            ))
        if year not in YEARS:
            continue
        annual_valid = {t: sum(bool(base.task_label(r, t)) for r in year_rows) for t, _ in TARGETS.values()}
        annual_positive = {t: sum(base.task_label(r, t) == label for r in year_rows) for t, label in TARGETS.values()}
        for code, sector in SECTORS.items():
            rows = [r for r in year_rows if r['gics_sector'] == sector]
            gv = sum(bool(base.task_label(r, 'governance')) for r in rows)
            ov = sum(bool(base.task_label(r, 'orientation')) for r in rows)
            gp = sum(base.task_label(r, 'governance') == 'Positive' for r in rows)
            op = sum(base.task_label(r, 'orientation') == 'Pro-AI' for r in rows)
            rates.append(dict(
                fiscal_year=year, gics_sector_code=code, gics_sector=sector,
                frame_n=len(rows), frame_sector_share_pct=percent(len(rows), len(year_rows)),
                governance_valid_n=gv, governance_positive_n=gp, governance_positive_rate=fraction(gp, gv),
                governance_positive_pct=percent(gp, gv), governance_excluded_n=len(rows) - gv,
                governance_valid_sample_sector_share_pct=percent(gv, annual_valid['governance']),
                orientation_valid_n=ov, pro_ai_n=op, pro_ai_rate=fraction(op, ov), pro_ai_pct=percent(op, ov),
                orientation_non_pro_ai_n=sum(base.task_label(r, 'orientation') == 'Non-Pro-AI' for r in rows),
                orientation_no_ai_discussion_n=sum(base.task_label(r, 'orientation') == 'No AI Discussion' for r in rows),
                orientation_excluded_n=len(rows) - ov,
                orientation_valid_sample_sector_share_pct=percent(ov, annual_valid['orientation']),
                both_tasks_valid_n=sum(bool(base.task_label(r, 'governance')) and bool(base.task_label(r, 'orientation')) for r in rows),
            ))
            for target, (task, label) in TARGETS.items():
                n, valid_n = (gp, gv) if task == 'governance' else (op, ov)
                share = fraction(n, annual_positive[task])
                baseline = fraction(valid_n, annual_valid[task])
                composition.append(dict(
                    fiscal_year=year, target_group=target, task=task, gics_sector_code=code, gics_sector=sector,
                    positive_n=n, annual_positive_n=annual_positive[task], share_within_positive=share,
                    share_within_positive_pct=100 * share if share is not None else None,
                    valid_classification_sector_n=valid_n, annual_valid_classification_n=annual_valid[task],
                    share_of_valid_sample_pct=100 * baseline if baseline is not None else None,
                    positive_share_minus_valid_sample_pp=100 * (share - baseline) if share is not None and baseline is not None else None,
                    relative_representation_ratio=share / baseline if share is not None and baseline else None,
                ))
    composition.sort(key=lambda r: (list(TARGETS).index(r['target_group']), r['fiscal_year'], r['gics_sector_code']))
    return composition, rates, coverage


def verify_summaries(composition, rates, coverage):
    for year in YEARS:
        rr = [r for r in rates if r['fiscal_year'] == year]
        require(len(rr) == 11 and sum(r['frame_n'] for r in rr) == 1500, 'Sector frame does not reconcile')
        for target, (task, _) in TARGETS.items():
            cc = [r for r in composition if r['fiscal_year'] == year and r['target_group'] == target]
            annual = next(r for r in coverage if r['fiscal_year'] == year and r['task'] == task)
            require(len(cc) == 11 and sum(r['positive_n'] for r in cc) == annual['positive_n'], 'Positive totals disagree')
            require(sum(r['valid_classification_sector_n'] for r in cc) == annual['valid_n'], 'Valid denominators disagree')
            require(abs(sum(r['share_within_positive'] for r in cc) - 1) < 1e-12, 'Composition does not sum to 100%')
            for r in cc:
                require(0 <= r['positive_n'] <= r['valid_classification_sector_n'], 'Positive outside valid denominator')
    require(all(r['pro_ai_n'] + r['orientation_non_pro_ai_n'] + r['orientation_no_ai_discussion_n'] == r['orientation_valid_n']
                for r in rates), 'Orientation denominator must include No AI Discussion')
    require(all(r['valid_n'] + r['excluded_n'] == r['frame_n'] and r['excluded_n'] ==
                sum(r[k] for k in ('missing_cik_n', 'double_unavailable_n', 'unresolved_n', 'runtime_holdout_n')) for r in coverage),
            'Coverage/exclusion accounting does not reconcile')


def plots():
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch
    from matplotlib.ticker import PercentFormatter
    plt = base.style.configure(OUT)
    lookup = {(r['target_group'], int(r['fiscal_year']), r['gics_sector_code']): r
              for r in read(OUT / 'annual_industry_composition.csv')}
    audits = {}
    titles = ('Industry Composition of AI Governance Positive Firms', 'Industry Composition of Pro-AI Firms')
    for number, (target, title) in enumerate(zip(TARGETS, titles), 1):
        slug = f'figure{number:02d}_{target}_industry_composition'
        fig, ax = plt.subplots(figsize=(14.4, 8.0))
        fig.subplots_adjust(left=.085, right=.975, top=.78, bottom=.32)
        base.style.title(fig, title, 'FY2023–FY2025  |  Denominator: all valid firm-years in the named positive disclosure category each year')
        bottom = [0.0] * len(YEARS)
        ns = [int(lookup[target, y, '10']['annual_positive_n']) for y in YEARS]
        for code in SECTORS:
            values = [float(lookup[target, y, code]['share_within_positive_pct']) for y in YEARS]
            bars = ax.bar(range(3), values, bottom=bottom, width=.52,
                          color=COLORS[code], edgecolor='white', linewidth=.65)
            require(all(abs(b.get_height() - v) < 1e-12 for b, v in zip(bars, values)), 'Plot/table disagreement')
            rgb = to_rgb(COLORS[code])
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
            luminance = sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
            label_color = 'white' if luminance < .24 else '#18212B'
            for x, value in enumerate(values):
                if value >= 5:
                    ax.text(x, bottom[x] + value / 2, f'{value:.1f}%', ha='center', va='center',
                            color=label_color, fontsize=10.5)
            bottom = [a + b for a, b in zip(bottom, values)]
        for x, (n, total) in enumerate(zip(ns, bottom)):
            require(n > 0 and abs(total - 100) < 1e-10, 'Nonempty stack must sum to 100%')
            ax.text(x, 1.025, f'N={n:,}', transform=ax.get_xaxis_transform(), ha='center', color='#596579', fontsize=10.5)
        ax.set(xlim=(-.6, 2.6), ylim=(0, 100), xlabel='Fiscal year', ylabel='Share within the annual positive disclosure category')
        ax.set_xticks(range(3), YEARS)
        ax.set_yticks(range(0, 101, 20))
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.xaxis.labelpad = 10
        base.style.grid(ax)
        # Three columns, ascending sector codes down each column, matching stacks bottom-to-top.
        legend = fig.legend(handles=[Patch(facecolor=COLORS[c], label=f'{c}  {s}') for c, s in SECTORS.items()],
                            loc='lower center', bbox_to_anchor=(.52, .105), ncol=3,
                            frameon=False, fontsize=10, columnspacing=2.8, labelspacing=.7, handlelength=1.8)
        base.style.footer(fig, 'GICS: fixed 19 Sep 2026 constituent snapshot applied to all years. Model labels; human semantic validation pending.\n'
                          'All 11 sectors are retained; segments below 5% have no percentage label. Legend and stack order follow sector codes.')
        fig.canvas.draw()
        box = legend.get_window_extent(fig.canvas.get_renderer())
        footer_boxes = [t.get_window_extent(fig.canvas.get_renderer()) for t in fig.texts if t.get_text().startswith('GICS:')]
        require(all(not box.overlaps(b) for b in footer_boxes), 'Legend overlaps footer')
        audits[slug] = dict(plotted_values_equal_csv=True, annual_stacks_sum_to_100=True,
                            annual_positive_n=ns, sector_codes=list(SECTORS), colors=COLORS,
                            bars_n=3, sectors_per_bar=11, label_threshold_pct=5,
                            legend_clear_of_footer=True, identical_axes_and_legend=True)
        base.save_figure(fig, slug, audits, output_dir=OUT, formats=('png',))
    dump(OUT / 'visual_qa.json', audits)
    return audits


def write_report(composition, rates, coverage, qa):
    comp = {(r['target_group'], r['fiscal_year'], r['gics_sector_code']): r for r in composition}
    rt = {(r['fiscal_year'], r['gics_sector_code']): r for r in rates}
    cv = {(r['fiscal_year'], r['task']): r for r in coverage}
    def share(target, year, code):
        return comp[target, year, code]['share_within_positive_pct']
    def pair(target, year):
        return sum(share(target, year, code) for code in ('40', '45'))
    lines = [
        '# AI 披露的年度行业构成（FY2023–FY2025）', '',
        f'分析版本：`{NAME}`；2026-10-28。复用已交付全样本 firm-year 最终标签，新增 LLM 调用 0，公司行业数据获取 0。', '',
        '**主要发现。**Governance Positive 三年均以 Financials 为最大行业、Information Technology 为第二大行业。'
        f'两者合计份额为 {pair("governance_positive", 2023):.2f}%、{pair("governance_positive", 2024):.2f}%、{pair("governance_positive", 2025):.2f}%。'
        f'Financials 从 {share("governance_positive", 2023, "40"):.2f}% 降至 {share("governance_positive", 2025, "40"):.2f}%，'
        f'Industrials 从 {share("governance_positive", 2023, "20"):.2f}% 升至 {share("governance_positive", 2025, "20"):.2f}%，'
        f'Health Care 从 {share("governance_positive", 2023, "35"):.2f}% 升至 {share("governance_positive", 2025, "35"):.2f}%。'
        '构成有所分散；FY2023 仅 35 个 Positive firm-years，小样本份额变动需谨慎解释。', '',
        f'Pro-AI 三年均以 Information Technology 份额最高，依次为 {share("pro_ai", 2023, "45"):.2f}%、'
        f'{share("pro_ai", 2024, "45"):.2f}%、{share("pro_ai", 2025, "45"):.2f}%；'
        f'Industrials 从 {share("pro_ai", 2023, "20"):.2f}% 升至 {share("pro_ai", 2025, "20"):.2f}%。'
        '两类披露在 FY2025 的前四大行业均为 Financials、Information Technology、Industrials 和 Health Care，次序不同。'
        f'Governance Positive 的 Financials 份额高于 Pro-AI {share("governance_positive", 2025, "40") - share("pro_ai", 2025, "40"):.2f} 个百分点；'
        f'Consumer Discretionary 份额低 {share("pro_ai", 2025, "25") - share("governance_positive", 2025, "25"):.2f} 个百分点。', '',
        '| FY | Governance 有效 N | Governance Positive n (%) | Orientation 有效 N | Pro-AI n (%) |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for y in YEARS:
        g, o = cv[y, 'governance'], cv[y, 'orientation']
        lines.append(f'| {y} | {g["valid_n"]:,} | {g["positive_n"]:,} ({percent(g["positive_n"], g["valid_n"]):.2f}%) | '
                     f'{o["valid_n"]:,} | {o["positive_n"]:,} ({percent(o["positive_n"], o["valid_n"]):.2f}%) |')
    lines += ['', '**行业内比例与样本构成。**FY2025 Governance Positive Rate 最高的是 Financials（16.80%）和 Information Technology（16.30%）；'
              'Pro-AI Rate 最高的是 Information Technology（65.93%）、Communication Services（57.78%）和 Health Care（53.90%）。'
              'Communication Services 的 Pro-AI 为 26/45，行业内比例较高，但在全部 Pro-AI 中仅占 4.26%，反映其较小的行业样本规模。', '',
              '原始固定框架中 Industrials、Financials、Information Technology 分别为 263、258、190 家（17.53%、17.20%、12.67%）。'
              'FY2025 在 Governance 有效样本中的份额为 17.39%、17.11%、12.59%，对应 Positive 构成为 14.88%、25.00%、17.86%；'
              '在 Orientation 有效样本中的份额为 17.46%、16.76%、12.76%，对应 Pro-AI 构成为 16.69%、17.02%、19.64%。'
              'Industrials 的较大 Positive 数量与其较大的样本基数有关；Financials 的 Governance Positive、Information Technology 的两类 Positive '
              '均高于其各自有效样本份额。Financials 的 Pro-AI 构成则接近样本基准。构成同时反映行业样本权重与行业内 Positive Rate。', '',
              '以下为 FY2025；FY2023–FY2025 全部 33 个 Sector-year 的有效 N、数量和比例见 [within_sector_positive_rates.csv](within_sector_positive_rates.csv)。', '',
              '| Sector | 原始框架 N | Governance Positive / 有效 N (%) | Pro-AI / 有效 N (%) |',
              '| --- | ---: | ---: | ---: |']
    for code, sector in SECTORS.items():
        r = rt[2025, code]
        lines.append(f'| {code} {sector} | {r["frame_n"]} | {r["governance_positive_n"]}/{r["governance_valid_n"]} '
                     f'({r["governance_positive_pct"]:.2f}%) | {r["pro_ai_n"]}/{r["orientation_valid_n"]} ({r["pro_ai_pct"]:.2f}%) |')
    lines += ['', '**来源与统计口径。**', '',
              '- Governance：`outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv`，版本 '
              '`implemented-internal-ai-governance-v2.0`；使用 `classification_status=complete` 且最终值为 0/1 的 firm-years，Positive 为 1。',
              '- Orientation：`data/interim/classifications/corporate_pro_ai_orientation/fullsample_v3_20261025/firm_year_panel.csv`，'
              'prompt `corporate-pro-ai-orientation-prompt-v3-20261024`；使用 `classification_status=classified` 的 '
              '`pro_ai`、`non_pro_ai`、`no_ai_discussion`；Positive 为 `pro_ai`。Governance v2.0 与 Orientation v3 的交付封存哈希及源 QA 均通过。',
              '- 年度构成分母为当年该类 Positive firm-year 总数；行业内比例分母为该 Sector-year 在该任务下的全部有效分类。'
              'Orientation 分母包含 No AI Discussion。两项任务分别取有效样本；未限制为两者同时有效。缺失、未解决、无有效来源和 runtime 示例留出保留排除状态。',
              '- 直接使用源最终 firm-year 标签，每个 CIK/FY 最多计一次，Item 1A 和 Item 7 不分别累加。'
              '沿用源 observed-section 聚合；有效 Pro-AI 标签可能伴随另一章节未解决，继续纳入，数量见年度覆盖表。',
              '- 框架与行业：`data/interim/documents/full_universe_item1a_manifest.csv`；与 '
              '`data/raw/universe/sp500.csv`、`sp400.csv`、`sp600.csv` 及各自 `.metadata.json` 逐公司交叉检查。'
              f'既有名称一一转为 [GICS 两位 Sector Code]({CODE_SOURCE})，未使用 Industry Group、Industry 或 Sub-Industry。',
              '- 行业为 **2026-09-19 抓取的固定成分快照**，应用于 FY2020–FY2025。metadata 的 `source_date` 为空，'
              '此日期记录抓取时点；数据不提供历史逐年行业归属或有效日期。未重新获取公司行业数据。', '',
              f'**匹配与覆盖检查。**原始框架 {qa["frame_firms_n"]:,} 家 × 6 年 = {qa["frame_n"]:,} 行；'
              f'{qa["nonempty_cik_fy_n"]:,} 个非空 CIK/FY 唯一，重复 0、未匹配 0、行业缺失/未知 0，行业映射覆盖 100%。'
              '另 1 家公司 6 年缺 CIK，仅用于原始框架排除审计。行业名称与原始快照、Orientation 面板完全一致，固定行业标签跨年一致。'
              '全部期间覆盖与排除原因见 [annual_classification_coverage.csv](annual_classification_coverage.csv)；'
              '逐项原始 CSV 独立回算结果见 [independent_validation.json](independent_validation.json)。', '',
              '**文件与复现。**两张 PNG 统一 300 dpi、0–100% 纵轴、Sector Code 顺序与颜色，每根柱子标注年度 Positive N；'
              '所有 11 个行业保留，低于 5% 的区段省略百分比文字。'
              '[annual_industry_composition.csv](annual_industry_composition.csv) 有 66 行，包含 Positive 数量、年度分母、行业构成及有效样本行业基准；'
              '[gics_sector_mapping.csv](gics_sector_mapping.csv) 保存 11 行代码、名称、颜色及固定快照属性。'
              '`*_rate`、`share_within_positive` 为 0–1，`*_pct` 为 0–100，`*_pp` 为百分点；缺少分母时留空。', '',
              '本目录按本次交付要求集中保存图、表、报告及 QA。复用 `firm_size_disclosure.load_data()`、既有 CSV/哈希工具、'
              '`governance_purpose_inductive_visualization` 绘图风格与 `firm_size_disclosure.save_figure()`；未新建中间面板。'
              '来源与代码 SHA256 见 [manifest.json](manifest.json)。复现：`python scripts/68_analyze_industry_within_disclosure.py`；'
              '独立校验：`python scripts/69_verify_industry_within_disclosure.py`；`--plots-only` 从 CSV 重绘，`--replace-derived` 仅重建本目录派生产物。', '',
              '这些结果描述自动分类的 10-K 披露，人工语义验证仍待完成；不据此推断实际治理效果、公司真实态度或因果关系。', '']
    (OUT / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plots-only', action='store_true')
    parser.add_argument('--replace-derived', action='store_true')
    args = parser.parse_args(argv)
    if args.plots_only:
        require(OUT.exists(), 'Prepare statistics before plotting')
        plots()
        return
    require(args.replace_derived or not OUT.exists(), 'Derived output exists; use --replace-derived')
    panel, lineage, hashes = load_analysis()
    composition, rates, coverage = summarize(panel)
    verify_summaries(composition, rates, coverage)
    qa = dict(passed=True, frame_n=len(panel), frame_firms_n=len(lineage),
              nonempty_cik_fy_n=sum(bool(r['cik']) for r in panel), missing_cik_fy_n=sum(not r['cik'] for r in panel),
              duplicate_cik_fy_n=0, unmatched_cik_fy_n=0, sector_mapping_coverage=1.0,
              missing_or_unknown_sector_n=0, orientation_frame_sector_conflicts_n=0,
              fixed_sector_across_years=True, source_seals_verified=True,
              independent_task_denominators=True, orientation_denominator_includes_no_ai_discussion=True,
              no_section_double_count=True, summary_reconciliation_passed=True,
              annual_composition_rows=len(composition), within_sector_rate_rows=len(rates), coverage_rows=len(coverage),
              source_versions=dict(governance='implemented-internal-ai-governance-v2.0', orientation='fullsample_v3_20261025'),
              llm_calls=0, company_industry_acquisition_calls=0, human_semantic_validation=False)
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / 'annual_industry_composition.csv', composition)
    write(OUT / 'within_sector_positive_rates.csv', rates)
    write(OUT / 'annual_classification_coverage.csv', coverage)
    write(OUT / 'gics_sector_mapping.csv', [dict(gics_sector_code=c, gics_sector=s, color=COLORS[c],
          frame_firms_n=sum(r['gics_sector'] == s and r['fiscal_year'] == 2025 for r in panel),
          snapshot_retrieval_date='2026-09-19', historical_time_varying=False, code_reference_url=CODE_SOURCE)
          for c, s in SECTORS.items()])
    write_report(composition, rates, coverage, qa)
    plots()
    qa['input_sha256_unchanged'] = all(file_hash(ROOT / path) == sha for path, sha in hashes.items())
    require(qa['input_sha256_unchanged'], 'Input source bytes changed')
    dump(OUT / 'qa.json', qa)
    code = [Path(__file__), ROOT / 'scripts/68_analyze_industry_within_disclosure.py',
            ROOT / 'scripts/69_verify_industry_within_disclosure.py',
            ROOT / 'src/ai_restrictions/firm_size_disclosure.py', ROOT / 'src/ai_restrictions/sampling.py',
            ROOT / 'src/ai_restrictions/governance_orientation_descriptive.py',
            ROOT / 'src/ai_restrictions/governance_purpose_inductive_visualization.py',
            ROOT / 'src/ai_restrictions/combined_governance_trends.py',
            ROOT / 'src/ai_restrictions/governance_adoption_dynamics.py', ROOT / 'src/ai_restrictions/governance_visualization.py']
    dump(OUT / 'manifest.json', dict(run_id=NAME, created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_versions=qa['source_versions'], input_sha256=hashes,
        code_sha256={p.relative_to(ROOT).as_posix(): file_hash(p) for p in code},
        output_sha256={p.name: file_hash(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json'},
        output_ownership='Requested final research figures, summary CSV tables, report and audit artifacts; no new source or interim data',
        sector_timing='Fixed 2026-09-19 retrieval snapshot applied to all fiscal years; source effective date unspecified',
        sector_code_reference=dict(url=CODE_SOURCE, checked_date='2026-10-28', company_labels_reacquired=False),
        python=sys.version, runtime_executable=sys.executable, llm_calls=0))
    print(json.dumps(qa, ensure_ascii=False))


if __name__ == '__main__':
    main()
