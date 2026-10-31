"""Build provenance catalogues for the already selected artifact; no new analysis."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from _prototype import ROOT, fields, read_csv, read_json, write_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures-only", action="store_true", help="Update only the figure registry and guide")
    args = parser.parse_args()
    sources = read_json(ROOT / "docs/figure_sources.json")
    specs = {
        "annual_positive_rate": dict(title="Annual Governance Positive rate", years="FY2020-FY2025", statistic="Positive rate", numerator="Governance Positive firm-years", denominator="All eligible classified firm-years in the fiscal year", sample="8500 eligible firm-years; observed-section OR; single-section observations retained", data="outputs/summary_statistics/governance/annual_trend_summary.csv", code="src/governance/ai_restrictions/governance_v2.py::figures", original_code="tmp/deepseek_global_config_20261025/before/src/ai_restrictions/governance_v2.py::figures"),
        "positive_size_composition": dict(title="Firm-size composition within Governance Positive", years="FY2020-FY2025", statistic="Conditional size composition", numerator="Positive firm-years in the size group and fiscal year", denominator="All Governance Positive firm-years in that fiscal year", sample="303 Positive firm-years; fixed S&P index size proxy", data="outputs/summary_statistics/governance/size_composition.csv", code="src/visualization/reference/firm_size_target_composition.py::plot_compositions", original_code="src/ai_restrictions/firm_size_target_composition.py::plot_compositions"),
        "positive_industry_composition": dict(title="GICS composition within Governance Positive", years="FY2023-FY2025", statistic="Conditional industry composition", numerator="Positive firm-years in the GICS sector and fiscal year", denominator="All Governance Positive firm-years in that fiscal year (35, 93, 168)", sample="296 Positive firm-years in FY2023-FY2025; all 11 GICS Sectors", data="outputs/summary_statistics/governance/annual_industry_composition.csv", code="src/visualization/reference/industry_target_composition.py::plots", original_code="src/ai_restrictions/industry_target_composition.py::plots"),
        "size_industry_annual_positive_rate": dict(title="Annual Size x Industry Governance Positive rate", years="FY2023-FY2025", statistic="Cell Positive rate (%)", numerator="Governance Positive firm-years within Year x Size x GICS Sector", denominator="Valid binary firm-years within the same cell", sample="4360 classified firm-years; 99 annual size-sector cells; 296 Positive", data="outputs/summary_statistics/governance/size_industry/year_size_sector_statistics.csv", code="src/visualization/reference/governance_size_industry.py::plot_figures", original_code="outputs/reports/governance_size_industry_v1_20261028/code_snapshot/src/ai_restrictions/governance_size_industry.py::plot_figures"),
        "size_industry_change_2023_2025": dict(title="Change in Size x Industry Governance Positive rates", years="FY2023 to FY2025", statistic="FY2025 minus FY2023 rate, percentage points", numerator="Difference between the two existing cell rates", denominator="Each endpoint has its own valid classified cell denominator", sample="33 size-sector cells; source small-N and sparse-Positive flags retained", data="outputs/summary_statistics/governance/size_industry/rate_changes.csv", code="src/visualization/reference/governance_size_industry.py::plot_figures", original_code="outputs/reports/governance_size_industry_v1_20261028/code_snapshot/src/ai_restrictions/governance_size_industry.py::plot_figures"),
        "size_industry_pooled_positive_rate": dict(title="Pooled Size x Industry Governance Positive rate", years="FY2023-FY2025 pooled", statistic="Pooled firm-year Positive rate (%)", numerator="Sum of Positive firm-years in the size-sector cell over the three years", denominator="Sum of valid classified firm-years in that cell over the three years", sample="4360 firm-year observations; 33 pooled cells; repeated firms across years count as firm-years", data="outputs/summary_statistics/governance/size_industry/pooled_statistics.csv", code="src/visualization/reference/governance_size_industry.py::plot_figures", original_code="outputs/reports/governance_size_industry_v1_20261028/code_snapshot/src/ai_restrictions/governance_size_industry.py::plot_figures"),
        "practice_distribution": dict(title="Distribution of disclosed governance practices", years="FY2020-FY2025", statistic="Distinct firm-year counts and prevalence", numerator="Positive firm-years assigned a Practice ID; deduplicated across evidence and sections", denominator="All 303 Governance Positive firm-years", sample="All 12 practices; 467 assignments; multi-label; zero-assignment and review cases retained in denominator", data="outputs/summary_statistics/practices/practice_category_statistics.csv [scope=all]", code="src/practices/ai_restrictions/governance_content_reporting.py::figures [Practice block]", original_code="outputs/implemented_ai_governance_content_analysis/code_snapshot/governance_content_reporting.py::figures"),
        "practice_annual_prevalence": dict(title="Practice prevalence within annual Governance Positive samples", years="FY2020-FY2025", statistic="Annual conditional firm-year prevalence (%)", numerator="Distinct annual Positive firm-years assigned the Practice ID", denominator="All Governance Positive firm-years in that fiscal year (2, 2, 3, 35, 93, 168)", sample="72 year-practice cells; multi-label; early years have only 2-3 Positive observations", data="outputs/summary_statistics/practices/practice_category_statistics.csv [scope=fiscal_year]", code="src/practices/ai_restrictions/governance_content_reporting.py::figures [annual Practice block]", original_code="outputs/implemented_ai_governance_content_analysis/code_snapshot/governance_content_reporting.py::figures"),
        "practice_annual_assignment_share": dict(title="Annual composition of Practice assignments", years="FY2020-FY2025; emphasis FY2023-FY2025", statistic="Share of annual firm-year-Practice assignments", numerator="Distinct annual firm-year assignments to the Practice ID", denominator="Annual sum of assignments over all 12 practices: 5, 5, 6, 54, 135, 262", sample="All 303 Positive firm-years; 467 assignments; 22 zero-assignment firm-years contribute no assignments", data="outputs/summary_statistics/practices/annual_practice_composition.csv; annual_assignment_totals.csv", code="src/visualization/reference/plot_governance_practices.py::figures", original_code="outputs/figures/governance_practices_v1_20261018_visualization_20261026/plot_governance_practices.py::figures"),
        "practice_annual_assignment_count": dict(title="Annual counts of Practice assignments", years="FY2020-FY2025; emphasis FY2023-FY2025", statistic="Stacked distinct firm-year counts by Practice", numerator="Distinct annual firm-year assignments to each Practice ID", denominator="No percentage denominator; bar height is annual total assignments, not unique firm-years", sample="All 12 practices; annual assignment totals 5, 5, 6, 54, 135, 262", data="outputs/summary_statistics/practices/annual_practice_composition.csv; annual_assignment_totals.csv", code="src/visualization/reference/plot_governance_practices.py::figures", original_code="outputs/figures/governance_practices_v1_20261018_visualization_20261026/plot_governance_practices.py::figures"),
    }
    overlay_path = ROOT / "docs/figure_presentation_updates.json"
    if overlay_path.is_file():
        by_id = {r["figure_id"]: r for r in sources}
        for update in read_json(overlay_path)["figures"]:
            identity = update["figure_id"]
            by_id[identity] = {k: update[k] for k in
                ("figure_id", "group", "prototype_png", "original_png", "visualization_run",
                 "classification_version", "available_formats")}
            specs.setdefault(identity, {}).update(update["spec"])
        sources = list(by_id.values())
    registry = []
    for original in sources:
        spec = specs[original["figure_id"]]
        registry.append(dict(original, title=spec["title"], fiscal_year_scope=spec["years"],
                             unit_of_analysis="firm-year; practice figures additionally deduplicate by Practice ID", statistic=spec["statistic"],
                             numerator=spec["numerator"], denominator=spec["denominator"], sample_scope=spec["sample"],
                             statistic_file=spec["data"], plotting_code=spec["code"], original_plotting_code=spec["original_code"],
                             original_project_root="C:/Users/62638/DESKTOP/不拥抱AI/ai-restrictions-concerns",
                             quality_status="Automated disclosure classifications; human semantic validation pending",
                             selection_basis=("Approved academic presentation update; measurement and categories unchanged"
                                 if original["visualization_run"] == "proposal_academic_v1_20261030" else
                                 "Distinct estimand, valid final classification lineage and readable original layout; redundant variants omitted")))
    write_csv(ROOT / "docs/figure_registry.csv", registry)

    overview = ("Eleven current figures comprise seven original views and four academic presentation panels. All ten historical images remain at their original prototype paths; the four updated panels have 300-dpi PNG and vector PDF companions. Their captions, denominators and transferred original qualifications are in [proposal_figure_notes.md](proposal_figure_notes.md). The [presentation overlay](figure_presentation_updates.json) records the update while preserving the initial source registry."
                if overlay_path.is_file() else
                "Ten original figures are retained as byte-identical copies. Existing PDF companions are included for six figures; the industry and Size × Industry source bundles supplied PNG only.")
    lines = ["# Guide to the selected figures", "", overview + " The [machine-readable registry](figure_registry.csv) records each source path, classification/visualization version, plotting function and statistic file.", "",
             "Governance rates condition on eligible classified observations. Composition figures condition on Positive observations or on Practice assignments. These denominators answer different descriptive questions.", ""]
    for index, row in enumerate(registry, 1):
        lines += [f"## {index}. {row['title']}", "", f"![{row['title']}](../{row['prototype_png']})", "",
                  f"Scope: {row['fiscal_year_scope']}. {row['sample_scope']}.", "",
                  f"Numerator: {row['numerator']}. Denominator: {row['denominator']}.", "",
                  f"Data: `{row['statistic_file']}`. Classification: `{row['classification_version']}`; visualization: `{row['visualization_run']}`.", ""]
    lines += ["## Interpretation and selection", "",
              "The binary annual trend and original Practice frequency/prevalence plots remain valid despite their earlier rendering date: later figures cite the same unchanged final datasets. The newer Practice composition plots use assignment shares, while the annual prevalence heatmap uses Positive firm-years. The three Size × Industry figures retain annual levels, endpoint changes and pooled levels as complementary views.", "",
              "Size/GICS membership is the fixed 19 September 2026 retrieval snapshot. Early FY2020–FY2022 Positive counts are only 2, 2 and 3. All plots describe model-coded observed disclosure, with human semantic validation pending.", "",
              "Portable replay uses copied drawing functions and bundled statistics. The initial ten-figure assembly evidence remains in `outputs/validation/figure_reproduction.json`; the current academic presentation replay is recorded separately in `outputs/validation/figure_reproduction_academic_20261030.json`.", ""]
    (ROOT / "docs/figures.md").write_text("\n".join(lines), encoding="utf-8")

    if args.figures_only:
        print(f"Registered {len(registry)} current figures; data catalogues and statistical tables unchanged.")
        return

    catalogue = []
    schemas = []
    for path in sorted(ROOT.rglob("*.csv")):
        relative = path.relative_to(ROOT)
        if "reproduced" in relative.parts or "tmp" in relative.parts or path.name in ["source_manifest.csv", "schema_inventory.csv", "data_catalogue.csv"]:
            continue
        rows = read_csv(path)
        columns = fields(path)
        catalogue.append(dict(prototype_path=relative.as_posix(), rows=len(rows), columns=len(columns)))
        schemas.extend(dict(prototype_path=relative.as_posix(), column_position=i + 1, column_name=column, rows=len(rows)) for i, column in enumerate(columns))
    write_csv(ROOT / "docs/data_catalogue.csv", catalogue)
    write_csv(ROOT / "docs/schema_inventory.csv", schemas)
    print(f"Registered {len(registry)} figures, {len(catalogue)} CSV tables and {len(schemas)} column definitions.")


if __name__ == "__main__":
    main()
