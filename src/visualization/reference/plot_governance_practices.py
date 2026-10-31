"""Offline, evidence-reconciled annual practice composition; no classification writes."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / 'pyproject.toml').is_file() and (p / 'src/ai_restrictions').is_dir())
SOURCE = ROOT / 'outputs/implemented_ai_governance_content_analysis'
NAME = 'governance_practices_v1_20261018_visualization_20261026'
DEFAULT_OUT = ROOT / 'outputs/figures' / NAME
STYLE_SOURCE = ROOT / 'src/ai_restrictions/governance_purpose_inductive_visualization.py'
# The delivered script uses its bundled, unchanged Purpose implementation.
STYLE = Path(__file__).with_name('purpose_plot_style.py')
if not STYLE.exists():
    STYLE = STYLE_SOURCE
spec = importlib.util.spec_from_file_location('purpose_plot_style', STYLE)
style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(style)
check, rows, read, sha = style.check, style.rows, style.read, style.sha


def load_data():
    names = ('firm_year_content_panel.csv', 'evidence_level_coding.csv',
             'assigned_category_quotes.csv', 'category_statistics.csv', 'codebook.json',
             'codebook.md', 'qa.json', 'independent_qa.json', 'data_dictionary.md',
             'review_queue.csv', 'run_report.md', 'delivery_manifest.json')
    inputs = {str((SOURCE / n).relative_to(ROOT).as_posix()): sha(SOURCE / n) for n in names}
    delivered = read(SOURCE / 'delivery_manifest.json')
    for n in names:
        if n != 'delivery_manifest.json':
            check(delivered['files'].get(n) == sha(SOURCE / n), 'Delivered input hash mismatch: ' + n)
    qa = read(SOURCE / 'qa.json')
    check(qa['integrity_passed'] and read(SOURCE / 'independent_qa.json')['passed'],
          'Existing integrity QA has not passed')
    check(qa['current_quote_validation_failures'] == qa['unknown_category_ids'] == 0,
          'Existing evidence validation has unresolved failures')
    check(sha(SOURCE / 'codebook.json') == qa['codebook_sha256'], 'Frozen codebook mismatch')
    categories = {c['id']: c['name'] for c in read(SOURCE / 'codebook.json')['categories']
                  if c['dimension'] == 'practices'}
    check(list(categories) == [f'P{i:02d}' for i in range(1, 13)], 'Practice category coverage changed')
    panel = rows(SOURCE / 'firm_year_content_panel.csv')
    key = lambda r: (r['cik'], int(r['fiscal_year']))
    bykey = {key(r): r for r in panel}
    check(len(bykey) == len(panel) == qa['panel_rows'], 'Duplicate or missing firm-years')
    binary = ROOT / 'outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv'
    inputs[binary.relative_to(ROOT).as_posix()] = sha(binary)
    expected = {key(r) for r in rows(binary) if r['implemented_internal_ai_governance_v2'] == '1'}
    check(set(bykey) == expected, 'Practice panel differs from original governance-Positive population')
    labels = {}
    for k, r in bykey.items():
        ls = json.loads(r['practices_categories'])
        check(len(ls) == len(set(ls)) and set(ls) <= set(categories), 'Invalid practice IDs')
        check(all(r[t] == str(int(t in ls)) for t in categories), 'Practice panel columns disagree')
        check(r['positive_binary_v2'] == '1' and r['failed_evidence_n'] == '0', 'Incomplete source coding')
        labels[k] = set(ls)

    evidence = rows(SOURCE / 'evidence_level_coding.csv')
    check(len({r['evidence_id'] for r in evidence}) == len(evidence) == qa['evidence_input_n'],
          'Duplicate/missing evidence rows')
    texts = {}; source_hashes = {}; support = set(); unflagged = set(); quote_keys = Counter()
    practice_quote_n = 0
    for e in evidence:
        k = key(e)
        check(k in bykey and e['binary_classification'] == 'Positive', 'Evidence population mismatch')
        ls = json.loads(e['practices'])
        if e['coding_status'] != 'coded' or e['uncodable'] != 'False':
            check(not ls, 'Uncodable/unvalidated evidence contributes practice labels')
            continue
        check(e['codebook_sha256'] == qa['codebook_sha256'], 'Evidence codebook mismatch')
        if not ls:
            continue
        rel = e['input_file']; p = ROOT / rel
        if rel not in texts:
            source_hashes[rel] = sha(p)
            texts[rel] = p.read_text(encoding='utf-8-sig')
        check(source_hashes[rel] == e['input_sha256'], 'Original TXT hash mismatch: ' + rel)
        text = texts[rel]
        check(text[int(e['evidence_start']):int(e['evidence_end'])] == e['evidence'],
              'Original binary evidence offset mismatch')
        blocks = json.loads(e['context_blocks'])
        for label in ls:
            t = label['category_id']; quote = label['quote']; locations = label['quote_locations']
            check(t in categories and t in labels[k], 'Evidence label missing from panel')
            check(quote.strip() and locations, 'Practice label lacks explicit source quote')
            for loc in locations:
                a, b = loc['start'], loc['end']
                check(0 <= a < b <= len(text) and text[a:b] == quote, 'Practice quote/offset mismatch')
                check(any(block['start'] <= a < b <= block['end'] for block in blocks),
                      'Practice quote outside supplied context')
            support.add((k, t))
            if e['review_flag'] == 'False':
                unflagged.add((k, t))
            quote_keys[(e['evidence_id'], t, quote, json.dumps(locations, sort_keys=True))] += 1
            practice_quote_n += 1
    check(support == {(k, t) for k, ls in labels.items() for t in ls},
          'A firm-year practice assignment lacks validated source evidence')
    exported = Counter((r['evidence_id'], r['category_id'], r['quote'],
                        json.dumps(json.loads(r['quote_locations']), sort_keys=True))
                       for r in rows(SOURCE / 'assigned_category_quotes.csv') if r['dimension'] == 'practices')
    check(exported == quote_keys, 'Practice quote export differs from coded evidence')
    freq = Counter(t for ls in labels.values() for t in ls)
    order = sorted(categories, key=lambda t: (-freq[t], t))
    years = list(range(2020, 2026)); annual = []; metrics = []
    for y in years:
        ks = [k for k in labels if k[1] == y]
        counts = {t: sum(t in labels[k] for k in ks) for t in categories}
        total = sum(counts.values())
        check(total > 0, 'Zero-assignment year needs explicit missing-year handling')
        annual.append(dict(fiscal_year=y, positive_firm_year_n=len(ks),
                           assigned_firm_year_n=sum(bool(labels[k]) for k in ks),
                           assignments=total, counts=counts))
        for t in order:
            metrics.append(dict(fiscal_year=y, practice_id=t, practice_name=categories[t],
                                firm_year_count=counts[t], annual_practice_assignments=total,
                                assignment_share=counts[t] / total,
                                assignment_percentage=100 * counts[t] / total,
                                governance_positive_firm_year_n=len(ks)))
    master = [r for r in rows(SOURCE / 'category_statistics.csv') if r['dimension'] == 'practices']
    expected_master = {(t, 'all', 'all') for t in categories} | {
        (t, 'fiscal_year', str(y)) for t in categories for y in years}
    used = [r for r in master if r['scope'] in ('all', 'fiscal_year')]
    check(len(used) == len(expected_master) and
          {(r['category_id'], r['scope'], r['scope_value']) for r in used} == expected_master,
          'Main statistics coverage mismatch')
    for r in used:
        t = r['category_id']
        if r['scope'] == 'all':
            count, den = freq[t], len(panel)
        else:
            a = annual[years.index(int(r['scope_value']))]
            count, den = a['counts'][t], a['positive_firm_year_n']
        check(r['category_name'] == categories[t], 'Category renamed')
        check(int(r['firm_year_count']) == count and int(r['denominator']) == den,
              'Main statistics count mismatch')
        check(abs(float(r['percentage']) - 100 * count / den) < 1e-9, 'Main prevalence mismatch')
    check(sum(freq.values()) == len(support) == sum(a['assignments'] for a in annual),
          'Overall assignments do not reconcile')
    return dict(inputs=inputs, source_hashes=source_hashes, panel=panel, themes=categories,
                order=order, freq=freq, years=years, annual=annual, metrics=metrics,
                assignment_n=len(support), practice_quote_n=practice_quote_n,
                multi_label_n=sum(len(ls) > 1 for ls in labels.values()),
                assignment_firm_year_n=sum(bool(ls) for ls in labels.values()),
                flagged_only_assignment_n=len(support - unflagged), qa=qa,
                master_cells_checked=len(used))


def figures(d, out):
    plt = style.configure(out)
    import numpy as np
    from matplotlib.colors import to_rgb
    from matplotlib.ticker import MaxNLocator, PercentFormatter
    colors = {t: style.PALETTE[i] for i, t in enumerate(d['themes'])}
    hatches = {t: ('//' if i >= 10 else '') for i, t in enumerate(d['themes'])}
    style.csvout(out / 'practice_color_map.csv', [dict(practice_id=t, practice_name=d['themes'][t],
                 color=colors[t], hatch=hatches[t], legend_order=i + 1) for i, t in enumerate(d['order'])])
    counts = np.array([[a['counts'][t] for a in d['annual']] for t in d['order']])
    totals = counts.sum(axis=0); shares = counts / totals
    check(np.allclose(shares.sum(axis=0), 1), 'Annual shares do not sum to 100%')
    x = np.arange(len(d['years'])); audits = {}
    for normalized, name in [(True, 'annual_governance_practices_composition_share'),
                             (False, 'annual_governance_practices_composition_count')]:
        fig = plt.figure(figsize=(16, 10.8)); ax = fig.add_axes([.08, .185, .45, .66])
        style.title(fig, 'Annual composition of AI governance practices' if normalized else
                    'Annual practice assignment counts',
                    'Figure 1  |  Share of annual practice assignments' if normalized else
                    'Figure 2  |  Firm-year counts within each practice')
        matrix = shares if normalized else counts; bottom = np.zeros(len(x))
        ax.axvspan(-.48, 2.48, color='#F0F2F3', zorder=0)
        for t, vals in zip(d['order'], matrix):
            bars = ax.bar(x, vals, bottom=bottom, color=colors[t], width=.67,
                          edgecolor='white', linewidth=.5, hatch=hatches[t], zorder=3)
            check(np.allclose([b.get_height() for b in bars], vals), 'Drawn segment/data mismatch')
            for j, v in enumerate(vals):
                if v >= (.067 if normalized else max(totals) * .06):
                    lum = sum(a * b for a, b in zip(to_rgb(colors[t]), (.2126, .7152, .0722)))
                    label = f'{t}\n{v:.0%}' if normalized else f'{t}\n{int(v)}'
                    ax.text(j, bottom[j] + v / 2, label, ha='center', va='center', fontsize=8.3,
                            color='white' if lum < .55 else '#17202A', zorder=4)
            bottom += vals
        for j, total in enumerate(totals):
            ax.text(j, 1.022 if normalized else total + max(totals) * .025,
                    f'A={total}', ha='center', va='bottom', fontsize=9.5)
        ax.set_xticks(x, [str(y) for y in d['years']]); ax.set_xlabel('Fiscal year', labelpad=11)
        if normalized:
            ax.set_ylim(0, 1.09); ax.set_yticks(np.arange(0, 1.01, .2))
            ax.yaxis.set_major_formatter(PercentFormatter(1))
            ax.set_ylabel('Share of annual practice assignments (%)')
        else:
            ax.set_ylim(0, max(totals) * 1.14); ax.set_ylabel('Firm-year observations by practice')
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        style.grid(ax); style.legend_axis(fig, d, colors, hatches)
        style.footer(fig,
            ('Composition denominator: annual A = sum of validated firm-year–practice assignments; multi-label.\n'
             if normalized else 'Segments: validated firm-years with each practice; stacked totals count practice assignments; multi-label.\n') +
            f"Total: {d['assignment_n']} assignments across {len(d['panel'])} governance-Positive firm-years (Item 1A / Item 7). One count per firm-year per practice; all 12 categories retained.\n" +
            'Shaded FY2020–FY2022: only 2–3 Positive firm-years/year; composition is unstable. Assignment shares differ from firm-year prevalence.\n' +
            'QA: source quotes and aggregation verified; automated disclosure labels; human semantic review pending.')
        style.save(fig, name, out, audits)
    return audits


def report(d, out):
    lines = ['# AI Governance Practices Annual Composition', '',
             '来源分类 Run：`implemented-ai-governance-content-v1-20261018`。', '',
             '## 数据与分母', '',
             '- 最终交付 firm-year 分类：`outputs/implemented_ai_governance_content_analysis/firm_year_content_panel.csv`。',
             '- 主统计：同目录 `category_statistics.csv`；冻结类别：`codebook.json` / `codebook.md`，P01–P12 全部保留。',
             '- Evidence：同目录 `evidence_level_coding.csv`、`assigned_category_quotes.csv`；QA：`qa.json`、`independent_qa.json`；输入哈希见 `visualization_manifest.json`。',
             '- 分子 n(k,t)：财年 t 有既有有效 Evidence 支持的 Practice k 的不同 firm-year 数。以 CIK×Fiscal Year×Practice 去重，跨 Item 1A / Item 7、多个引文均只计一次。',
             '- 年度分母 A(t)=Σk n(k,t)；组成 Share(k,t)=n(k,t)/A(t)。图2色块为 n(k,t)，堆叠柱高为 A(t)。',
             '- 样本为原 Governance v2 Positive firm-years。未观察到 Practice 的 firm-years 不贡献 assignment；保留其状态，不追加缺失类或负类。', '',
             '## QA 范围与结果', '',
             'Practice 数据没有 Purpose 的 `qa_passed` / `semantic_verdict` 字段，也没有 Practice 级 Explicit/Implicit 标记。此次采用既有技术 QA：成功编码、非 uncodable、有非空原文引文和位置、原 TXT SHA-256 匹配、引文逐字与位置匹配且位于提供的上下文内、Evidence—panel—主统计一致。显性 Evidence 在这里指现有标签具有可定位的原文支持；此次未新增语义判定。', '',
             f"现有 QA 标记完整性通过；重新检查 {d['practice_quote_n']} 个 Practice Evidence 标签、{len(d['source_hashes'])} 个支持 TXT 和 {d['master_cells_checked']} 个全期/年度主统计单元格，全部一致。所有 {d['assignment_n']} 个去重 assignments 均有有效支持；年度相加=全期主统计相加。所有年度组成之和=100%。", '',
             f"样本 {len(d['panel'])} 个 firm-years，{len({r['cik'] for r in d['panel']})} 家公司；{d['assignment_firm_year_n']} 个至少有一个 Practice，{d['multi_label_n']} 个有多个。未观察到 Practice 的 {len(d['panel'])-d['assignment_firm_year_n']} 个 firm-years 不增加分母 A。", '',
             f"保留既有主统计中的有引文标签，包括仅由模型 review_flag Evidence 支持的 {d['flagged_only_assignment_n']} 个 assignments。review_flag 是待复核标记，现有主统计未将其移除；单独剔除会改变本次要求复用的样本口径。原交付待人工复核队列 {d['qa']['review_queue_evidence_n']} 条，人工完成数 {d['qa']['human_reviews_completed']}。技术 QA 与独立人工语义验证分别记录；图中结果仍为自动披露分类。", '',
             '|Fiscal year|Governance-Positive firm-years|至少一项 Practice 的 firm-years|Assignments A|',
             '|---|---:|---:|---:|']
    for a in d['annual']:
        lines.append(f"|FY{a['fiscal_year']}|{a['positive_firm_year_n']}|{a['assigned_firm_year_n']}|{a['assignments']}|")
    lines += ['', '## FY2023–FY2025 组成', '',
              '年度 assignments 从54增至135、262。P01 框架、政策与程序的组成占比从31.5%升至44.4%、44.7%，增加主要出现在FY2023→FY2024。P04 测试、验证与风险评估从14.8%降至8.4%，对应计数从8增至22；P03 用例审查与审批从13.0%降至8.8%，计数从7增至23。两者的相对权重下降伴随绝对计数增长。P02 跨职能治理机构与委员会在FY2025占7.3%，高于FY2023的5.6%。', '',
              '|Practice ID 与冻结名称|FY2023 n / share|FY2024 n / share|FY2025 n / share|2023→2025 pp|',
              '|---|---:|---:|---:|---:|']
    for t in d['order']:
        recent = d['annual'][3:]
        vals = [a['counts'][t] / a['assignments'] * 100 for a in recent]
        cells = [f"{a['counts'][t]} / {v:.1f}%" for a, v in zip(recent, vals)]
        lines.append(f"|{t} {d['themes'][t]}|" + '|'.join(cells) + f'|{vals[-1]-vals[0]:+.1f}|')
    lines += ['', 'FY2023–FY2025 的构成变化与绝对 assignment 增长应分别阅读。所有比例描述所分析 10-K 披露中的 Practice 标签组成；不直接表示企业治理实践采用率、治理效果或因果关系。FY2020–FY2022 每年仅2–3个 Positive firm-years，5–6个 assignments，灰底标记其组成不稳定。', '',
              '## 版式与复现', '',
              '直接复用 `src/ai_restrictions/governance_purpose_inductive_visualization.py` 的 PALETTE、configure、title、footer、grid、legend_axis、save。16×10.8英寸、DejaVu Sans、300 dpi、左右轴区/图例布局、灰底和标注阈值保持 Purpose Annual Composition 风格。颜色按冻结 P ID 顺序固定，堆叠及图例按全期计数降序；12类均保留且使用不同颜色。大色块阈值为6.7%；计数图为最大年度 A 的6%。附 PNG 与 PDF。', '',
              '项目根目录执行：`.venv/Scripts/python.exe scripts/63_plot_governance_practices.py`。', '',
              '也可运行本目录 `plot_governance_practices.py`，使用同目录保存的 `purpose_plot_style.py`；支持 `--output-dir`。依赖 matplotlib、numpy。源模块位于 `src/ai_restrictions/governance_practices_visualization.py`。此流程不含 LLM 请求或既有分类写入。', '',
              '`annual_practice_composition.csv` 保存72个年度×类别绘图值；`annual_assignment_totals.csv` 保存年度样本数和 A；`practice_color_map.csv` 保存固定配色；`visualization_qa.json` 保存数值及画布检查；manifest记录输入、代码、输出哈希与依赖版本。', '']
    (out / 'visualization_report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(); out = args.output_dir.resolve()
    check(out != SOURCE.resolve(), 'Output must not overwrite source classification directory')
    d = load_data(); out.mkdir(parents=True, exist_ok=True)
    audits = figures(d, out)
    style.csvout(out / 'annual_practice_composition.csv', d['metrics'])
    style.csvout(out / 'annual_assignment_totals.csv', [{k: v for k, v in a.items() if k != 'counts'} for a in d['annual']])
    report(d, out)
    if Path(__file__).resolve() != (out / 'plot_governance_practices.py'):
        shutil.copyfile(__file__, out / 'plot_governance_practices.py')
    if STYLE.resolve() != (out / 'purpose_plot_style.py'):
        shutil.copyfile(STYLE, out / 'purpose_plot_style.py')
    protected = {**d['inputs'], **d['source_hashes']}
    changed = [p for p, h in protected.items() if sha(ROOT / p) != h]
    check(not changed, 'Source inputs changed during plotting: ' + repr(changed))
    qa = dict(passed=True, classification_inputs_unchanged=True, assignments=d['assignment_n'],
              annual_assignments={a['fiscal_year']: a['assignments'] for a in d['annual']},
              practice_categories=len(d['themes']), practice_quote_labels=d['practice_quote_n'],
              source_txt_hashes_verified=len(d['source_hashes']),
              master_statistics_cells_reconciled=d['master_cells_checked'],
              evidence_panel_set_equality=True, main_statistics_equality=True,
              annual_shares_sum_to_100=True, qa_type='technical source/aggregation QA',
              human_semantic_validation=False, human_reviews_completed=d['qa']['human_reviews_completed'],
              flagged_only_assignments=d['flagged_only_assignment_n'], figures=audits)
    style.dump(out / 'visualization_qa.json', qa)
    import matplotlib, numpy
    manifest = dict(visualization_id=NAME, source_run='implemented-ai-governance-content-v1-20261018',
                    generated_utc=datetime.now(timezone.utc).isoformat(), python=sys.version,
                    matplotlib=matplotlib.__version__, numpy=numpy.__version__,
                    style_source=STYLE_SOURCE.relative_to(ROOT).as_posix(), style_sha256=sha(STYLE),
                    input_sha256=d['inputs'], supporting_txt_sha256=d['source_hashes'],
                    implementation_sha256=sha(Path(__file__)),
                    outputs_sha256={p.name: sha(p) for p in sorted(out.iterdir())
                                    if p.is_file() and p.name != 'visualization_manifest.json'})
    style.dump(out / 'visualization_manifest.json', manifest)
    print(json.dumps(dict(output=str(out), assignments=d['assignment_n'],
                         annual_assignments=qa['annual_assignments'], qa_passed=True)))


if __name__ == '__main__':
    main()
