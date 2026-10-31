"""One-time, copy-only assembly of the audited research artifact.

Run only in a fresh prototype directory. Existing destinations are never replaced.
No acquisition, LLM call, classification, or original-project writer is invoked.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G = "outputs/full_universe_implemented_internal_ai_governance_v2"
P = "outputs/implemented_ai_governance_content_analysis"
PV = "outputs/figures/governance_practices_v1_20261018_visualization_20261026"
SI = "governance_size_industry_v1_20261028"
SC = "firm_size_within_disclosure_composition_v1_20261026"
IC = "outputs/figures/industry_within_disclosure_composition_v1_20261028"
GV = "implemented-internal-ai-governance-v2.0"
PR = "implemented-ai-governance-content-v1-20261018"
RECORDS: list[dict] = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), reader.fieldnames


def target(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Destination outside prototype")
    if path.exists():
        raise FileExistsError(f"Refusing to replace an existing destination: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def sensitive_bytes(data):
    # Key names and credential resolver code are expected; credential values are not.
    return bool(re.search(rb"\bsk-[A-Za-z0-9_-]{20,}\b", data) or
                re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data))


def record(source_paths, dest, purpose, version, basis, operation, transformation="", row_n=""):
    RECORDS.append(dict(
        prototype_path=dest.relative_to(ROOT).as_posix(),
        original_project_path=json.dumps([str(p.resolve()) for p in source_paths], ensure_ascii=False),
        original_relative_path=json.dumps([p.relative_to(SOURCE).as_posix() for p in source_paths], ensure_ascii=False),
        file_type=dest.suffix.lstrip("."), purpose=purpose,
        classification_version=version, run_id=PR if version.startswith("implemented-ai-governance-content") else "",
        run_identity=("full_universe_implemented_internal_ai_governance_v2; started_at_utc=2026-10-13T08:45:17.873118+00:00" if version == GV else version),
        selection_basis=basis, operation=operation, transformation=transformation,
        source_sha256=json.dumps([sha(p) for p in source_paths]),
        prototype_sha256=sha(dest), bytes=dest.stat().st_size, rows=row_n,
    ))


def copy(relative, dest, purpose, version, basis):
    src = SOURCE / relative
    data = src.read_bytes()
    if src.name == ".env" or sensitive_bytes(data):
        raise ValueError(f"Sensitive file excluded: {relative}")
    output = target(dest)
    shutil.copyfile(src, output)
    assert sha(src) == sha(output)
    row_n = len(read_csv(output)[0]) if output.suffix == ".csv" else ""
    record([src], output, purpose, version, basis, "byte-identical copy", row_n=row_n)
    return output


def generated_csv(relative, rows, fields, sources, purpose, version, transformation):
    output = target(relative)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    record([SOURCE / p for p in sources], output, purpose, version,
           "Exact view of audited existing records; no new model labels", "deterministic view", transformation, len(rows))


def generated_json(relative, value, sources, purpose, version, transformation):
    output = target(relative)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record([SOURCE / p for p in sources], output, purpose, version,
           "Exact selection or compact provenance of audited existing artifacts", "deterministic view", transformation,
           len(value) if isinstance(value, list) else "")


def generated_text(relative, text, sources, purpose, version, transformation):
    output = target(relative)
    output.write_text(text, encoding="utf-8")
    record([SOURCE / p for p in sources], output, purpose, version,
           "Exact runtime message scaffold recovered from the frozen source and checked against an original saved request",
           "runtime template extracted from original code", transformation)


def frozen_package(kind, seeds, overrides):
    """Preserve original import names and copy only their static local dependency closure."""
    backup = SOURCE / "tmp/deepseek_global_config_20261025/before/src/ai_restrictions"
    live = SOURCE / "src/ai_restrictions"
    output_base = f"src/{kind}/ai_restrictions"

    def find(module):
        if module in overrides:
            return SOURCE / overrides[module]
        part = Path(*module.split(".")) if module else Path()
        for base in (backup, live):
            for file in (base / part.with_suffix(".py"), base / part / "__init__.py") if module else (base / "__init__.py",):
                if file.is_file():
                    return file
        return None

    queue = [""] + list(seeds)
    visited = set()
    while queue:
        module = queue.pop(0)
        if module in visited:
            continue
        source = find(module)
        if source is None:
            raise FileNotFoundError(f"Unresolved historical dependency: {kind}:{module}")
        visited.add(module)
        package = source.name == "__init__.py"
        part = module.replace(".", "/")
        suffix = f"{part}/__init__.py" if package and part else "__init__.py" if package else part + ".py"
        copy(source.relative_to(SOURCE).as_posix(), f"{output_base}/{suffix}",
             "Frozen core module" if module in seeds else "Import dependency of frozen core; no independent research output",
             GV if kind == "governance" else "implemented-ai-governance-content-v1.0",
             "Final delivery hash match for core; pre-20261025 dependency snapshot; historical client kept separately for each workflow")
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        context = module.split(".") if package and module else module.split(".")[:-1]
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.level:
                continue
            prefix = context[:len(context) - node.level + 1]
            if node.module:
                name = ".".join(prefix + node.module.split("."))
                dependency = find(name)
                if dependency:
                    queue.append(name)
                    if dependency.name == "__init__.py":
                        for alias in node.names:
                            candidate = name + "." + alias.name
                            if find(candidate):
                                queue.append(candidate)
            else:
                for alias in node.names:
                    candidate = ".".join(prefix + [alias.name])
                    if find(candidate):
                        queue.append(candidate)


def assemble():
    # These read-only audit files were written only after the original project audit completed.
    audit = read_json(ROOT / "outputs/validation/project_audit_20261029.json")
    assert all(not v.get("mismatches") for k, v in audit["checks"].items() if k.endswith("delivery_hashes"))
    final_hashes = read_json(SOURCE / G / "delivery_manifest.json")["final_code_hashes"]
    for relative, expected in final_hashes.items():
        historical = SOURCE / "tmp/deepseek_global_config_20261025/before" / relative
        assert sha(historical) == expected, f"Historical final-code mismatch: {relative}"

    for name in ["combined_firm_year_v2_panel.csv", "item1a_v2_classification_results.csv", "item7_v2_classification_results.csv",
                 "input_manifest.csv", "exclusion_manifest.csv", "source_exception_manifest.csv", "positive_evidence_audit.csv"]:
        copy(f"{G}/{name}", f"data/full_sample/governance/{name}",
             "Complete native full-universe result or source/coverage audit", GV,
             "Complete sealed v2 delivery; final firm-year panel, independent delivery QA, and matching downstream figure hashes")
    copy(f"{G}/annual_trend_summary.csv", "outputs/summary_statistics/governance/annual_trend_summary.csv", "Annual observed-section OR counts and rates", GV, "Sealed final v2 aggregate")
    copy(f"{G}/classification_standard_snapshot.md", "config/governance_guidelines/implemented_internal_ai_governance_v2.md", "Authoritative frozen binary guideline", GV, "Matches current authoritative guideline and both frozen deliveries")
    for name in ["system_prompt.txt", "user_prompt_template.txt", "llm_config.json", "recovery_llm_config.json", "recovery_round2_llm_config.json",
                 "validation_retry_user_suffix_template.txt", "validation_retry_user_suffix_template_round2.txt"]:
        copy(f"{G}/{name}", f"config/governance_prompts/{name}", "Historical full prompt or request configuration", GV, "Saved run snapshot; no retrofit of 20261025 thinking settings")
    for name in ["run_manifest.json", "delivery_manifest.json", "run_report.md", "delivery_qa.json", "qa.json", "offline_test_summary.json",
                 "classification_exception_queue.csv", "offline_recovery_unresolved.csv", "corrective_recovery_summary.csv", "semantic_source_review_manifest.csv", "cost_and_token_summary.json"]:
        copy(f"{G}/{name}", f"outputs/validation/governance/{name}", "Historical execution, exception, recovery, QA or delivery metadata", GV, "Final delivered run, including zero-row unresolved queues")
    copy("docs/implemented_governance_v2_workflow.md", "docs/provenance/implemented_governance_v2_workflow.md", "Original workflow and explicit observed-section estimator convention", GV, "Documents why delivered aggregation differs from the strict two-section guideline")

    for name in ["firm_year_content_panel.csv", "evidence_level_coding.json", "evidence_source_index.csv", "category_statistics.csv", "assigned_category_quotes.csv"]:
        copy(f"{P}/{name}", f"data/full_sample/practices/native/{name}", "Unchanged native shared content-coding source needed to reproduce P01-P12", "implemented-ai-governance-content-v1.0", "Frozen completed closed-coding delivery; all 303 firm-years and 403 evidence units; shared dimensions retained as method dependencies")
    copy("data/interim/classifications/implemented_ai_governance_content_analysis/v1/evidence_units.json", "data/full_sample/practices/native/evidence_units.json", "All 403 bounded-context evidence inputs", "implemented-ai-governance-content-v1.0", "Exact original closed-coding input units; full context enables offline source-quote checks")
    for name in ["codebook.json", "codebook.md", "coding_schema.json", "system_prompt.txt", "user_prompt_template.txt", "open_coding_system_prompt.txt", "open_coding_user_prompt_template.txt", "codebook_synthesis_system_prompt.txt", "llm_config.json"]:
        copy(f"{P}/{name}", f"config/practices_prompts/{name}", "Frozen codebook, schema, complete historical prompt or configuration", "implemented-ai-governance-content-v1.0", "Frozen codebook hash eb145750...a698; P01-P12 unchanged; shared three-dimension schema required by original validator")
    for name in ["run_manifest.json", "delivery_manifest.json", "qa.json", "independent_qa.json", "offline_test_summary.json", "coding_failures.csv", "review_queue.csv", "request_validation_issues.csv", "codebook_refinement_audit.json", "context_supplement_manifest.json", "closed_coding_pilot_gate.json", "cost_and_token_summary.json"]:
        copy(f"{P}/{name}", f"outputs/validation/practices/{name}", "Historical frozen-run QA, failure and pending-review provenance", "implemented-ai-governance-content-v1.0", "Automatic integrity passed; no human review completed; unresolved/uncodable states preserved")
    for name in ["run_report.md", "data_inventory.md", "data_dictionary.md"]:
        copy(f"{P}/{name}", f"docs/provenance/practices/{name}", "Original shared content-coding method and execution record", "implemented-ai-governance-content-v1.0", "Native joint run retained as provenance; later Governance Purpose research modules excluded")
    copy(f"{P}/exploration_sample.csv", "data/sample/codebook_development_sample.csv", "Original 50-firm-year maximum-variation codebook development sample", "implemented-ai-governance-content-v1.0", "Method provenance; not an independent validation set")

    frozen_package("governance", ["governance_v2", "governance_v2_recovery", "governance_v2_delivery"], {
        "governance_v2": "tmp/deepseek_global_config_20261025/before/src/ai_restrictions/governance_v2.py",
        "governance_v2_recovery": "tmp/deepseek_global_config_20261025/before/src/ai_restrictions/governance_v2_recovery.py",
        "llm.client": f"{G}/code_snapshot/client.py", "llm.governance_v2_prompt": f"{G}/code_snapshot/governance_v2_prompt.py",
    })
    frozen_package("practices", ["governance_content", "governance_content_reporting"], {
        "governance_content": f"{P}/code_snapshot/governance_content.py",
        "governance_content_reporting": f"{P}/code_snapshot/governance_content_reporting.py",
        "llm.client": f"{P}/code_snapshot/client.py", "llm.content_analysis_prompt": f"{P}/code_snapshot/content_analysis_prompt.py",
    })
    for kind, names in [("governance", ["39_classify_governance_v2.py", "40_recover_governance_v2.py", "41_verify_governance_v2_delivery.py"]),
                        ("practices", ["43_analyze_governance_content.py", "44_verify_governance_content.py"])]:
        for name in names:
            base = "tmp/deepseek_global_config_20261025/before/scripts"
            path = f"{base}/{name}"
            if not (SOURCE / path).exists():
                path = f"scripts/{name}"
            copy(path, f"src/{kind}/reference_entrypoints/{name}", "Original historical entry point; archival and external-layout dependent", GV if kind == "governance" else "implemented-ai-governance-content-v1.0", "Preserved for inspection; supported portable execution is through scripts/reproduce.py")
    copy(f"{P}/code_snapshot/refine_governance_content_codebook.py", "src/practices/reference_entrypoints/refine_governance_content_codebook.py", "Historical codebook refinement procedure", "implemented-ai-governance-content-v1.0", "Existing refinement only; not executed during assembly")

    # Exact practice views preserve every eligible row and all review/absence distinctions.
    panel, fields = read_csv(SOURCE / P / "firm_year_content_panel.csv")
    practice_fields = fields[:fields.index("practices_categories") + 1] + [f"P{i:02}" for i in range(1, 13)]
    generated_csv("data/full_sample/practices/firm_year_practices_panel.csv", panel, practice_fields,
                  [f"{P}/firm_year_content_panel.csv"], "Primary all-positive firm-year practice panel", "implemented-ai-governance-content-v1.0", "Column projection only; all 303 rows retained; original flags unchanged")
    evidence = read_json(SOURCE / P / "evidence_level_coding.json")
    evidence_fields = [k for k in evidence[0] if k not in {"motivations", "visions", "motivation_status", "vision_status", "motivation_explicitness", "vision_explicitness", "emerging_themes"}]
    ev_csv = [{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in e.items()} for e in evidence]
    generated_csv("data/full_sample/practices/evidence_level_practices.csv", ev_csv, evidence_fields,
                  [f"{P}/evidence_level_coding.json"], "Practice evidence with all 403 input records and uncertainty flags", "implemented-ai-governance-content-v1.0", "Column projection; native JSON retains original emerging themes and joint dimensions")
    for name, output in [("assigned_category_quotes.csv", "practice_quotes.csv"), ("category_statistics.csv", "practice_category_statistics.csv")]:
        rows, fields = read_csv(SOURCE / P / name)
        selected = [x for x in rows if x["dimension"] == "practices"]
        folder = "data/full_sample/practices" if name.startswith("assigned") else "outputs/summary_statistics/practices"
        generated_csv(f"{folder}/{output}", selected, fields, [f"{P}/{name}"], "Complete P01-P12 quote or descriptive-statistic view", "implemented-ai-governance-content-v1.0", "Row filter dimension=practices; all practice labels retained; no firm-year sampling")

    # Existing fixed index/sector metadata, with unrelated Orientation fields omitted.
    metadata_path = "data/interim/panels/firm_size_ai_disclosure_v1_20261026/firm_year_size_panel.csv"
    metadata, _ = read_csv(SOURCE / metadata_path)
    generated_csv("data/reference/firm_year_metadata.csv", metadata,
                  ["cik", "ticker", "company_name", "fiscal_year", "firm_id", "firm_size_group", "index_name", "gics_sector", "identity_status"],
                  [metadata_path], "All 9000 frame records, fixed size and GICS mapping only", "fixed-source-snapshot-20260919", "Column projection only; all frame rows retained, including six missing-CIK audit rows")
    for index in ["500", "400", "600"]:
        for ext in ["csv", "metadata.json"]:
            name = f"sp{index}.{ext}"
            copy(f"data/raw/universe/{name}", f"data/reference/universe/{name}", "Immutable index/sector snapshot provenance", "fixed-source-snapshot-20260919", "Existing sample frame; no new constituent acquisition")

    # Curated figure statistics and their byte-identical provenance records.
    size_path = f"outputs/tables/{SC}/target_group_size_composition_tidy.csv"
    size, fields = read_csv(SOURCE / size_path)
    generated_csv("outputs/summary_statistics/governance/size_composition.csv", [x for x in size if x["target_group"] == "governance_positive"], fields, [size_path], "Governance-Positive size composition", SC, "Row filter governance_positive; 18 existing cells, identical values")
    for name in ["annual_industry_composition.csv", "annual_classification_coverage.csv", "within_sector_positive_rates.csv"]:
        vals, fields = read_csv(SOURCE / IC / name)
        if "target_group" in fields:
            vals = [x for x in vals if x["target_group"] == "governance_positive"]
        # Paired tables carry Orientation columns; keep the entire Governance side.
        unrelated = {"both_tasks_valid_n", "positive_with_unresolved_companion_n", "runtime_holdout_n", "no_ai_discussion_n"}
        fields = [f for f in fields if not any(t in f.lower() for t in ["orientation", "pro_ai"]) and not f.startswith("o_") and f not in unrelated]
        if "task" in fields:
            vals = [x for x in vals if x.get("task") == "governance"]
        generated_csv(f"outputs/summary_statistics/governance/{name}", vals, fields, [f"{IC}/{name}"], "Existing Governance industry/coverage statistics", "industry_within_disclosure_composition_v1_20261028", "Governance-only row/column view; unchanged statistics")
    copy(f"{IC}/gics_sector_mapping.csv", "data/reference/gics_sector_mapping.csv", "GICS names, codes, colors and snapshot timing", "industry_within_disclosure_composition_v1_20261028", "11 saved Sector labels; no new sector assignment")
    for source_path, name in [
        ("data/interim/documents/full_universe_item1a_manifest.csv", "item1a_source_manifest.csv"),
        ("data/interim/documents/full_universe_item7/optimization_v2/manifest_item7-secondary-v2.4.csv", "item7_source_manifest.csv"),
    ]:
        copy(source_path, f"data/reference/source_manifests/{name}", "Upstream filing URLs, accession, extraction and raw-source retention provenance", GV, "Existing owning manifests captured at assembly; frozen classification input_manifest remains authoritative for classified text bytes")
    for name in ["year_size_sector_statistics.csv", "pooled_statistics.csv", "rate_changes.csv", "marginal_statistics.csv", "size_gaps.csv", "coverage_sensitivity.csv"]:
        copy(f"outputs/tables/{SI}/{name}", f"outputs/summary_statistics/governance/size_industry/{name}", "Existing FY2023-FY2025 size-sector descriptive statistic", SI, "Latest completed pure-Governance analysis, using sealed v2 firm-year panel")
    for name in ["annual_practice_composition.csv", "annual_assignment_totals.csv", "practice_color_map.csv"]:
        copy(f"{PV}/{name}", f"outputs/summary_statistics/practices/{name}", "Existing practice assignment composition or figure encoding", PR, "20261026 visualization is a restyling of the same frozen 20261018 coding")
    figure_data, fields = read_csv(SOURCE / P / "figure_data.csv")
    generated_csv("outputs/summary_statistics/practices/selected_figure_data.csv", [x for x in figure_data if x["figure"] in {"01_practices_frequency", "04_practices_by_year"}], fields, [f"{P}/figure_data.csv"], "Original frequency and annual-prevalence figure cells", "implemented-ai-governance-content-v1.0", "Keep only the two selected Practice figures; identical values")
    for source_dir, dest_dir, names in [
        (f"outputs/reports/{SI}", "size_industry", ["manifest.json", "qa.json", "independent_qa.json", "visual_qa.json", "report.md"]),
        (f"outputs/reports/{SC}", "size_composition", ["manifest.json", "qa.json", "visual_qa.json"]),
        (IC, "industry_composition", ["manifest.json", "qa.json", "independent_validation.json", "visual_qa.json"]),
        (PV, "practice_composition", ["visualization_manifest.json", "visualization_qa.json", "visualization_report.md"]),
    ]:
        for name in names:
            copy(f"{source_dir}/{name}", f"outputs/validation/figures/{dest_dir}/{name}", "Original figure lineage, QA and denominator evidence", PR if source_dir == PV else SI if dest_dir == "size_industry" else SC if dest_dir == "size_composition" else "industry_within_disclosure_composition_v1_20261028", "Classification input hashes and independently checked statistical cells match selected final datasets")

    figures = [
        (f"{G}/figures", "governance", "figure1_annual_positive_rate", "annual_positive_rate", ["png", "pdf"], GV),
        (f"outputs/figures/{SC}", "governance", "figure01_governance_positive_firm_size_composition", "positive_size_composition", ["png", "pdf"], SC),
        (IC, "governance", "figure01_governance_positive_industry_composition", "positive_industry_composition", ["png"], "industry_within_disclosure_composition_v1_20261028"),
        (f"outputs/figures/{SI}", "governance", "figure1_annual_positive_rate", "size_industry_annual_positive_rate", ["png"], SI),
        (f"outputs/figures/{SI}", "governance", "figure2_rate_change_2023_2025", "size_industry_change_2023_2025", ["png"], SI),
        (f"outputs/figures/{SI}", "governance", "figure3_pooled_positive_rate", "size_industry_pooled_positive_rate", ["png"], SI),
        (f"{P}/figures", "practices", "01_practices_frequency", "practice_distribution", ["png", "pdf"], PR),
        (f"{P}/figures", "practices", "04_practices_by_year", "practice_annual_prevalence", ["png", "pdf"], PR),
        (PV, "practices", "annual_governance_practices_composition_share", "practice_annual_assignment_share", ["png", "pdf"], PR),
        (PV, "practices", "annual_governance_practices_composition_count", "practice_annual_assignment_count", ["png", "pdf"], PR),
    ]
    registry = []
    for folder, group, name, slug, formats, version in figures:
        for ext in formats:
            copy(f"{folder}/{name}.{ext}", f"figures/{group}/{slug}.{ext}", "Curated original research figure", GV if version in [GV, SI, SC, "industry_within_disclosure_composition_v1_20261028"] else "implemented-ai-governance-content-v1.0", f"Chosen for distinct content and readable layout; visualization version {version}; newer pie variants are redundant")
        registry.append(dict(figure_id=slug, group=group, prototype_png=f"figures/{group}/{slug}.png", original_png=f"{folder}/{name}.png", visualization_run=version, classification_version=GV if group == "governance" else "implemented-ai-governance-content-v1.0", available_formats=",".join(formats)))
    generated_json("docs/figure_sources.json", registry, [f"{G}/delivery_manifest.json", f"{P}/delivery_manifest.json"], "Curated figure identities and original paths", "prototype-assembly-20261029", "Registry only; no new figure or analysis")

    for relative, name in [
        ("src/ai_restrictions/firm_size_target_composition.py", "firm_size_target_composition.py"),
        ("src/ai_restrictions/industry_target_composition.py", "industry_target_composition.py"),
        (f"outputs/reports/{SI}/code_snapshot/src/ai_restrictions/governance_size_industry.py", "governance_size_industry.py"),
        ("src/ai_restrictions/firm_size_disclosure.py", "firm_size_disclosure.py"),
        (f"{PV}/plot_governance_practices.py", "plot_governance_practices.py"),
        (f"{PV}/purpose_plot_style.py", "purpose_plot_style.py"),
    ]:
        copy(relative, f"src/visualization/reference/{name}", "Unmodified plotting reference; portable adapter invokes selected existing functions only", PR if relative.startswith(PV) else SI if name.startswith("governance_size") else "existing-visualization-20261026-20261028", "Preserve existing plot logic and style; data paths supplied by portable offline adapter")

    # Five native source sections provide early, boundary, dual-section and negative examples.
    all_sections = []
    for section in ["item1a", "item7"]:
        vals, section_fields = read_csv(SOURCE / G / f"{section}_v2_classification_results.csv")
        all_sections.extend(vals)
    choices = {("AXP", "2020", "item7"), ("DEA", "2025", "item1a"), ("GM", "2023", "item1a"), ("GM", "2023", "item7"), ("A", "2020", "item1a")}
    samples = [x for x in all_sections if (x["ticker"], x["fiscal_year"], x["section"]) in choices]
    assert len(samples) == 5
    sample_manifest = []
    for row in samples:
        filename = Path(row["input_file"]).name
        dest = f"data/sample/texts/{filename}"
        copy(row["input_file"], dest, "Native 10-K section for offline prompt and response validation", GV, "Deterministic existing examples; not a classification-accuracy evaluation sample")
        sample_manifest.append(dict(ticker=row["ticker"], cik=row["cik"], fiscal_year=row["fiscal_year"], section=row["section"], original_input_file=row["input_file"], local_input_file=dest, input_sha256=row["input_sha256"], classification=row["classification"]))
    generated_csv("data/sample/section_results.csv", samples, section_fields, [f"{G}/item1a_v2_classification_results.csv", f"{G}/item7_v2_classification_results.csv"], "Existing sample section model outputs; all original columns preserved", GV, "Select the five documented existing source sections")
    generated_csv("data/sample/manifest.csv", sample_manifest, list(sample_manifest[0]), [f"{G}/input_manifest.csv"], "Sample local-path bridge; native records retain original paths", GV, "Explicit mapping only; text bytes and hashes unchanged")
    original_request = "data/interim/classifications/implemented_ai_governance_content_analysis/v1/requests/closed/0000004962_FY2020_item7_E01__1.json"
    copy(original_request, "data/sample/practices_closed_request.json", "Exact saved closed-coding request, without credentials", "implemented-ai-governance-content-v1.0", "Original AXP FY2020 Item 7 evidence request; runtime builder and payload hash verified")
    generated_text("config/practices_prompts/runtime_user_prompt_template.txt", "FROZEN CODEBOOK: {codebook_json}\nEVIDENCE UNIT: {evidence_unit_json}",
                   [f"{P}/code_snapshot/governance_content.py"], "Exact runtime closed-coding user-message scaffold", "implemented-ai-governance-content-v1.0", "Original inline closed_coding builder; saved readability template separately preserved with its extra trailing Return instruction")
    generated_text("config/practices_prompts/validation_correction_user_suffix_template.txt", "\nValidation correction required: {last_error}. Return corrected exact JSON; preserve the same codebook and original text.",
                   [f"{P}/code_snapshot/governance_content.py"], "Historical validation-correction suffix scaffold", "implemented-ai-governance-content-v1.0", "Exact suffix from the frozen call function; last_error is supplied by the original finite corrective retry logic")

    # Failure-event records keep retry history distinct from final unresolved observations.
    for kind, history in audit["request_history"].items():
        events = []
        fields = ["original_record_number", "request_id", "status", "timestamp_utc", "cik", "ticker", "fiscal_year", "section", "stage", "evidence_or_batch_id", "prompt_version", "attempt", "validation_request", "payload_sha256", "error"]
        with (SOURCE / history["original_path"]).open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not any(t in obj.get("status", "") for t in ["error", "failure", "queued"]):
                    continue
                event = {k: obj.get(k, "") for k in fields}
                event["original_record_number"] = number
                event["timestamp_utc"] = obj.get("timestamp_utc", obj.get("time_utc", ""))
                if isinstance(event["error"], (dict, list)):
                    event["error"] = json.dumps(event["error"], ensure_ascii=False)
                events.append(event)
        generated_csv(f"outputs/validation/{kind}/historical_failure_events.csv", events, fields, [history["original_path"]], "Compact complete historical failure/error/semantic-queue event log", GV if kind == "governance" else "implemented-ai-governance-content-v1.0", "Select status containing error, failure or queued; retain record IDs and provenance; event counts are not final failed-observation counts")
    generated_json("outputs/validation/request_history_summary.json", audit["request_history"], [audit["request_history"][k]["original_path"] for k in ["governance", "practices"]], "Full original request-log hashes and complete event counts", "prototype-assembly-20261029", "Summary of existing logs; bulky request/response caches remain in original project")

    output = ROOT / "outputs/validation/assembly_records.json"
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(RECORDS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"copied_or_derived_files": len(RECORDS), "bytes": sum(x["bytes"] for x in RECORDS), "source_project_modified": False, "llm_calls": 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-project", type=Path, required=True)
    args = parser.parse_args()
    SOURCE = args.source_project.resolve()
    if SOURCE == ROOT or SOURCE.is_relative_to(ROOT):
        raise ValueError("Source project must be outside prototype")
    assemble()
