"""Replay selected historical and academic presentation figures from bundled data.

Historical plotting modules combine several projects and resolve old repository
paths at import time. We compile only the named, copied function definitions,
then bind their data paths and shared style explicitly. The original source files
remain byte-identical. The joint content figure function is restricted to its
existing practice-frequency and annual-practice blocks, as documented below.
"""
from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import json
import math
import os
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from _prototype import (ROOT, PDATA, PIDS, load_frozen, read_csv, read_json,
                        replay_output, require, sha, write_json)

REFERENCE = ROOT / "src/visualization/reference"
EXTRACTIONS = []


def selected_definitions(path, names, bindings, practice_blocks_only=False):
    """Load explicitly named definitions; do not execute historical module setup."""
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    chosen = []
    found = set()
    for node in tree.body:
        node_names = ({node.name} if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else
                      {x.id for x in node.targets if isinstance(x, ast.Name)} if isinstance(node, ast.Assign) else set())
        if not (node_names & set(names)):
            continue
        found |= node_names & set(names)
        source_hash = hashlib.sha256(ast.get_source_segment(text, node).encode()).hexdigest()
        EXTRACTIONS.append(dict(source=path.relative_to(ROOT).as_posix(), definitions=sorted(node_names & set(names)),
                                source_definition_sha256=source_hash,
                                selection="practice blocks only" if practice_blocks_only else "verbatim definition; paths bound by adapter"))
        node = copy.deepcopy(node)
        if practice_blocks_only:
            body = []
            for statement in node.body:
                # Everything from practice co-occurrence onward belongs to unselected figures.
                if isinstance(statement, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "co" for x in statement.targets):
                    break
                # The original three-dimension loop is restricted to its first, practice tuple.
                if isinstance(statement, ast.For) and isinstance(statement.target, ast.Tuple):
                    if [x.id for x in statement.target.elts if isinstance(x, ast.Name)] == ["dim", "name", "title"]:
                        statement.iter.elts = statement.iter.elts[:1]
                body.append(statement)
            node.body = body
        chosen.append(node)
    require(set(names) <= found, "Missing copied plotting definition: " + repr(set(names) - found))
    namespace = dict(bindings)
    module = ast.fix_missing_locations(ast.Module(body=chosen, type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in names})


def typed_table(path):
    def cast(value):
        if value == "":
            return None
        if value in ["True", "False"]:
            return value == "True"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return [{k: cast(v) for k, v in row.items()} for row in read_csv(path)]


def academic_presentations(output, common, style, data, sectors, stats, sizes):
    """Bind the copied pure presentation functions to local tables and export paths."""
    import matplotlib
    overlay = read_json(ROOT / "docs/figure_presentation_updates.json")
    destination = output / "academic_presentation"
    destination.mkdir(parents=True, exist_ok=True)
    matplotlib.rcdefaults()
    style.configure(destination)
    matplotlib.rcParams.update({"font.size": 8.5, "axes.labelsize": 9,
                                "pdf.fonttype": 42, "hatch.linewidth": .4})
    bindings = dict(common, check=require, WORK=ROOT, FIGURES=destination,
                    PREVIEW=destination / "previews", YEARS=(2023, 2024, 2025),
                    SIZES=sizes, SECTORS=list(sectors.values()), SMALL_N=20, SPARSE_P=5,
                    SOURCE_ASSETS={f["slug"]: ROOT / f["prototype_png"] for f in overlay["figures"]})
    drawing = selected_definitions(ROOT / "src/visualization/academic_presentation.py",
        ["annual_rate_figure", "academic_pies", "academic_annual_heatmap",
         "academic_exclusion_bars", "export"], bindings)
    expected, audits = {}, {}
    by_id = {f["figure_id"]: f for f in overlay["figures"]}

    def save(identity, fig, audit, labels=()):
        spec = by_id[identity]
        audits[identity] = drawing.export(fig, spec["slug"], audit, labels)
        expected[spec["prototype_png"]] = destination / (spec["slug"] + ".png")

    annual = typed_table(stats / "governance/annual_trend_summary.csv")
    fig, audit = drawing.annual_rate_figure(annual)
    save("annual_positive_rate", fig, audit)
    color_map = {r["practice_id"]: r for r in read_csv(stats / "practices/practice_color_map.csv")}
    fig, audit, labels = drawing.academic_pies(data, color_map)
    save("practice_annual_assignment_share", fig, audit, labels)
    tab = stats / "governance/size_industry"
    cells, pooled = typed_table(tab / "year_size_sector_statistics.csv"), typed_table(tab / "pooled_statistics.csv")
    fig, audit = drawing.academic_annual_heatmap(cells, pooled)
    save("size_industry_annual_positive_rate", fig, audit)

    def pooled_metric(rows):
        positive, valid = sum(r["positive_n"] for r in rows), sum(r["total_n"] for r in rows)
        require(valid > 0, "Missing pooled denominator; do not impute a comparison bar")
        return dict(positive_n=positive, total_n=valid, positive_rate_pct=100 * positive / valid)

    comparison = []
    for group in sizes:
        rows = [r for r in pooled if r["firm_size_group"] == group]
        comparison.append(dict(size=group, all_industries=pooled_metric(rows),
            excluding_financials_it=pooled_metric([r for r in rows if r["gics_sector"] not in
                                                  ("Financials", "Information Technology")])))
    fig, audit = drawing.academic_exclusion_bars(comparison)
    save("size_industry_exclusion_comparison", fig, audit)
    return expected, audits


def replay_figures(output):
    output = Path(output).resolve()
    require(output.is_relative_to(ROOT / "outputs/reproduced"), "Figure replay must remain within outputs/reproduced")
    output.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(output / "_matplotlib_cache")
    import matplotlib
    from PIL import Image, ImageChops
    EXTRACTIONS.clear()
    matplotlib.use("Agg")

    common = dict(ROOT=ROOT, Path=Path, os=os, json=json, csv=csv, textwrap=textwrap,
                  math=math, Counter=Counter, defaultdict=defaultdict, require=require)
    style = selected_definitions(REFERENCE / "purpose_plot_style.py",
                                 ["PALETTE", "NAVY", "rows", "sha", "read", "csvout", "check", "wrap", "configure", "title", "footer", "grid", "save", "legend_axis"], common)
    base_defs = selected_definitions(REFERENCE / "firm_size_disclosure.py", ["SIZE_COLORS", "SIZES", "YEARS", "save_figure"], common)
    base = SimpleNamespace(style=style, save_figure=base_defs.save_figure, SIZE_COLORS=base_defs.SIZE_COLORS,
                           SIZES=base_defs.SIZES, YEARS=base_defs.YEARS)
    expected = {}
    audits = {}
    stats = ROOT / "outputs/summary_statistics"

    # Governance trend: unchanged historical renderer and saved annual statistics.
    matplotlib.rcdefaults()
    trend = output / "governance/trend"
    trend.mkdir(parents=True, exist_ok=True)
    governance = load_frozen("governance")
    governance.OUT = trend
    annual = typed_table(stats / "governance/annual_trend_summary.csv")
    governance.figures(annual)
    expected["figures/governance/annual_positive_rate.png"] = trend / "figures/figure1_annual_positive_rate.png"

    # Size composition: the original function receives the Governance target only.
    matplotlib.rcdefaults()
    size = output / "governance/size"
    size.mkdir(parents=True, exist_ok=True)
    bindings = dict(common, base=base, FIGURES=size, TABLES=stats / "governance", YEARS=base.YEARS, SIZES=base.SIZES,
                    TARGETS={"governance_positive": ("governance", "Positive")},
                    TITLES={"governance_positive": "Firm-Size Composition among Firms with Implemented AI Governance"},
                    read=lambda path: read_csv(stats / "governance/size_composition.csv"))
    renderer = selected_definitions(REFERENCE / "firm_size_target_composition.py", ["plot_compositions"], bindings)
    audits["size_composition"] = renderer.plot_compositions()
    expected["figures/governance/positive_size_composition.png"] = size / "figure01_governance_positive_firm_size_composition.png"

    # Industry composition: same 11 codes, colors and conditional denominator.
    matplotlib.rcdefaults()
    industry = output / "governance/industry"
    industry.mkdir(parents=True, exist_ok=True)
    sector_rows = read_csv(ROOT / "data/reference/gics_sector_mapping.csv")
    sectors = {x["gics_sector_code"]: x["gics_sector"] for x in sector_rows}
    colors = {x["gics_sector_code"]: x["color"] for x in sector_rows}
    bindings = dict(common, base=base, OUT=industry, YEARS=(2023, 2024, 2025), SECTORS=sectors, COLORS=colors,
                    TARGETS={"governance_positive": ("governance", "Positive")},
                    read=lambda path: read_csv(stats / "governance/annual_industry_composition.csv"),
                    dump=lambda path, value: write_json(path, value))
    renderer = selected_definitions(REFERENCE / "industry_target_composition.py", ["plots"], bindings)
    audits["industry_composition"] = renderer.plots()
    expected["figures/governance/positive_industry_composition.png"] = industry / "figure01_governance_positive_industry_composition.png"

    # Three complementary Size x Industry figures; all original cell flags retained.
    matplotlib.rcdefaults()
    cross = output / "governance/size_industry"
    cross.mkdir(parents=True, exist_ok=True)
    bindings = dict(common, base=base, FIGURES=cross, REPORT=cross, YEARS=(2023, 2024, 2025), SIZES=base.SIZES,
                    SECTORS=list(sectors.values()), SMALL_N=20, SPARSE_P=5,
                    dump=lambda path, value: write_json(path, value))
    renderer = selected_definitions(REFERENCE / "governance_size_industry.py", ["plot_figures"], bindings)
    tab = stats / "governance/size_industry"
    audits["size_industry"] = renderer.plot_figures(typed_table(tab / "year_size_sector_statistics.csv"),
                                                   typed_table(tab / "pooled_statistics.csv"), typed_table(tab / "rate_changes.csv"))
    for original, slug in [("figure1_annual_positive_rate", "size_industry_annual_positive_rate"),
                           ("figure2_rate_change_2023_2025", "size_industry_change_2023_2025"),
                           ("figure3_pooled_positive_rate", "size_industry_pooled_positive_rate")]:
        expected[f"figures/governance/{slug}.png"] = cross / (original + ".png")

    # Original content renderer restricted to its existing practice-only blocks.
    matplotlib.rcdefaults()
    content = output / "practices/content"
    content.mkdir(parents=True, exist_ok=True)
    p, reporting = load_frozen("practices")
    p.OUT = content
    panel = read_json(PDATA / "native/evidence_level_coding.json")
    units = read_json(PDATA / "native/evidence_units.json")
    book = read_json(ROOT / "config/practices_prompts/codebook.json")
    native_panel = reporting.aggregate(units, {e["evidence_id"]: e for e in panel}, book)
    practice_book = dict(book, categories=[c for c in book["categories"] if c["dimension"] == "practices"])
    renderer = selected_definitions(ROOT / "src/practices/ai_restrictions/governance_content_reporting.py", ["figures"], dict(common, g=p), practice_blocks_only=True)
    renderer.figures(practice_book, native_panel, [], [], [])
    expected["figures/practices/practice_distribution.png"] = content / "figures/01_practices_frequency.png"
    expected["figures/practices/practice_annual_prevalence.png"] = content / "figures/04_practices_by_year.png"

    # Original 20261026 assignment-composition renderer, supplied from native P01-P12 counts.
    matplotlib.rcdefaults()
    composition = output / "practices/annual"
    composition.mkdir(parents=True, exist_ok=True)
    themes = {c["id"]: c["name"] for c in practice_book["categories"]}
    freq = {t: sum(row[t] for row in native_panel) for t in themes}
    order = sorted(themes, key=lambda t: (-freq[t], t))
    years = list(range(2020, 2026))
    annual = []
    for year in years:
        ps = [row for row in native_panel if row["fiscal_year"] == year]
        counts = {t: sum(row[t] for row in ps) for t in themes}
        annual.append(dict(fiscal_year=year, positive_firm_year_n=len(ps), assigned_firm_year_n=sum(any(row[t] for t in themes) for row in ps), counts=counts, assignments=sum(counts.values())))
    data = dict(themes=themes, order=order, years=years, annual=annual, panel=native_panel, assignment_n=sum(freq.values()))
    renderer = selected_definitions(REFERENCE / "plot_governance_practices.py", ["figures"], dict(common, style=style, check=require))
    audits["practice_composition"] = renderer.figures(data, composition)
    expected["figures/practices/practice_annual_assignment_share.png"] = composition / "annual_governance_practices_composition_share.png"
    expected["figures/practices/practice_annual_assignment_count.png"] = composition / "annual_governance_practices_composition_count.png"

    # Current presentation overlay: historical source images and renderers are retained.
    overlay_path = ROOT / "docs/figure_presentation_updates.json"
    if overlay_path.is_file():
        original_sources = {r["figure_id"]: r for r in read_json(ROOT / "docs/figure_sources.json")}
        for spec in read_json(overlay_path)["figures"]:
            if spec["figure_id"] in original_sources:
                expected.pop(original_sources[spec["figure_id"]]["prototype_png"], None)
        academic, audits["academic_presentation"] = academic_presentations(
            output, common, style, data, sectors, stats, base.SIZES)
        expected.update(academic)

    comparisons = []
    for original, recreated in expected.items():
        with Image.open(ROOT / original) as a, Image.open(recreated) as b:
            equal_pixels = a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
        comparisons.append(dict(prototype_figure=original, replay_path=recreated.relative_to(ROOT).as_posix(),
                                original_sha256=sha(ROOT / original), replay_sha256=sha(recreated),
                                equal_png_bytes=sha(ROOT / original) == sha(recreated), equal_rgb_pixels=equal_pixels))
    require(set(expected) == {r["prototype_png"] for r in read_csv(ROOT / "docs/figure_registry.csv")},
            "Selected figure coverage differs from the current registry")
    report = dict(llm_calls=0, selected_figures_replayed=len(comparisons),
                  byte_identical_png_n=sum(x["equal_png_bytes"] for x in comparisons),
                  pixel_identical_png_n=sum(x["equal_rgb_pixels"] for x in comparisons),
                  comparisons=comparisons, original_function_extractions=EXTRACTIONS,
                  renderer_checks=audits, runtime=dict(matplotlib=matplotlib.__version__),
                  scope="Bundled frozen data and copied historical/presentation drawing functions; no inference or new empirical analysis")
    write_json(output / "figure_replay_report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="outputs/reproduced/figures")
    args = parser.parse_args()
    report = replay_figures(replay_output(args.output_dir))
    print(json.dumps({k: report[k] for k in ["llm_calls", "selected_figures_replayed", "byte_identical_png_n", "pixel_identical_png_n"]}, indent=2))
