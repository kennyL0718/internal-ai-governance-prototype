"""Portable, offline adapters for the unmodified historical measurement code."""
from __future__ import annotations

import csv
import hashlib
import importlib
import importlib.util
import json
import os
import re
import socket
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
GDATA = ROOT / "data/full_sample/governance"
PDATA = ROOT / "data/full_sample/practices"
PIDS = [f"P{i:02}" for i in range(1, 13)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def fields(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return csv.DictReader(stream).fieldnames


def write_csv(path, data, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(data[0])
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                             if isinstance(row.get(k), (dict, list)) else row.get(k, "") for k in columns})


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def no_network(*args, **kwargs):
    raise RuntimeError("This prototype entry point supports offline replay only")


def block_network():
    """Fail closed if any accidental network or credential-dependent path is reached."""
    socket.create_connection = no_network
    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    urllib.request.urlopen = no_network


def load_frozen(kind):
    block_network()
    prefix = "_prototype_frozen_" + kind
    package_dir = ROOT / "src" / kind / "ai_restrictions"
    if prefix not in sys.modules:
        spec = importlib.util.spec_from_file_location(prefix, package_dir / "__init__.py",
                                                     submodule_search_locations=[str(package_dir)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[prefix] = package
        spec.loader.exec_module(package)
    client = importlib.import_module(prefix + ".llm.client")
    for name in ["_transport", "chat_json", "load_config", "smoke_test"]:
        setattr(client, name, no_network)
    if kind == "governance":
        module = importlib.import_module(prefix + ".governance_v2")
        module.ROOT = ROOT
        module.STANDARD = ROOT / "config/governance_guidelines/implemented_internal_ai_governance_v2.md"
        module.system.cache_clear()
        return module
    module = importlib.import_module(prefix + ".governance_content")
    module.ROOT = ROOT
    reporting = importlib.import_module(prefix + ".governance_content_reporting")
    return module, reporting


def result_from_section(row):
    return dict(classification=row["classification"], evidence=json.loads(row["evidence"]),
                reason=row["reason"], manual_review_needed=row["manual_review_needed"] == "True",
                review_reason=row["review_reason"], mechanism_summary=row["mechanism_summary"],
                temporal_basis=row["temporal_basis"], scope_limitation=row["scope_limitation"])


def normal(value):
    if isinstance(value, str) and value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    if isinstance(value, (list, dict)):
        return value
    return "" if value is None else str(value)


def key(row):
    return row["cik"], str(row["fiscal_year"])


def compare_rows(actual, expected, columns, label):
    actual_by_key = {key(x): x for x in actual}
    expected_by_key = {key(x): x for x in expected}
    require(len(actual_by_key) == len(actual), label + ": duplicate actual keys")
    require(len(expected_by_key) == len(expected), label + ": duplicate expected keys")
    require(actual_by_key.keys() == expected_by_key.keys(), label + ": key sets differ")
    errors = []
    for identity, wanted in expected_by_key.items():
        observed = actual_by_key[identity]
        for column in columns:
            if normal(observed.get(column)) != normal(wanted.get(column)):
                errors.append([list(identity), column])
    require(not errors, f"{label}: cell differences {errors[:8]}")
    return dict(rows=len(actual), columns=len(columns), unequal_cells=0)


def governance_replay():
    g = load_frozen("governance")
    states = read_csv(GDATA / "input_manifest.csv")
    for row in states:
        for column in ["text_available", "accession_conflict"]:
            row[column] = row[column] == "True"
    sections = read_csv(GDATA / "item1a_v2_classification_results.csv") + read_csv(GDATA / "item7_v2_classification_results.csv")
    records = {}
    for row in sections:
        if row["classification_status"] == "complete":
            records[g.key(row)] = dict(status="complete", result=result_from_section(row),
                                      quote_locations=json.loads(row["evidence_locations"]),
                                      prompt_version=row["prompt_version"], classified_at_utc=row["classified_at_utc"])
    _, combined = g.aggregate(states, records)
    eligible = [x for x in combined if x["classification_status"] == "complete"]
    excluded = [x for x in combined if x["classification_status"] == "excluded_double_unavailable"]
    panel_columns = fields(GDATA / "combined_firm_year_v2_panel.csv")
    checks = dict(
        firm_year_panel=compare_rows(eligible, read_csv(GDATA / "combined_firm_year_v2_panel.csv"), panel_columns, "Governance panel"),
        exclusion_panel=compare_rows(excluded, read_csv(GDATA / "exclusion_manifest.csv"), panel_columns, "Governance exclusions"),
        final_records_n=len(records), frame_firm_year_n=len(combined),
    )
    require(len(combined) == 9000 and len(eligible) == 8500 and len(excluded) == 500, "Governance coverage mismatch")
    require(sum(x["implemented_internal_ai_governance_v2"] == "1" for x in eligible) == 303, "Governance positive count mismatch")
    # Independently reconcile the existing annual summary; no alternate estimator is created.
    for annual in read_csv(ROOT / "outputs/summary_statistics/governance/annual_trend_summary.csv"):
        year = annual["fiscal_year"]
        ps = [x for x in eligible if str(x["fiscal_year"]) == year]
        positive_n = sum(x["implemented_internal_ai_governance_v2"] == "1" for x in ps)
        require(len(ps) == int(annual["eligible_n"]) and positive_n == int(annual["positive_n"]), "Annual count mismatch")
        require(abs(positive_n / len(ps) - float(annual["positive_rate"])) < 1e-14, "Annual rate mismatch")
    checks["annual_counts_and_rates_match"] = True
    return eligible, excluded, checks


def practices_replay():
    p, reporting = load_frozen("practices")
    units = read_json(PDATA / "native/evidence_units.json")
    evidence = read_json(PDATA / "native/evidence_level_coding.json")
    codebook_path = ROOT / "config/practices_prompts/codebook.json"
    codebook = read_json(codebook_path)
    require(sha(codebook_path) == read_json(ROOT / "outputs/validation/practices/run_manifest.json")["codebook_sha256"], "Frozen codebook hash differs")
    by_id = {x["evidence_id"]: x for x in evidence}
    require(len(by_id) == len(evidence) == len(units) == 403, "Evidence input/coding coverage mismatch")
    for unit in units:
        p.validate_observation(by_id[unit["evidence_id"]], unit, codebook)
    panel = reporting.aggregate(units, by_id, codebook)
    native_path = PDATA / "native/firm_year_content_panel.csv"
    native_check = compare_rows(panel, read_csv(native_path), fields(native_path), "Native practice aggregation")
    practice_path = PDATA / "firm_year_practices_panel.csv"
    primary_check = compare_rows(panel, read_csv(practice_path), fields(practice_path), "Practice view")
    primary = [{k: row[k] for k in fields(practice_path)} for row in panel]
    assignments = {(x["cik"], str(x["fiscal_year"]), cid) for x in panel for cid in PIDS if x[cid]}
    quotes = read_csv(PDATA / "practice_quotes.csv")
    support = {(x["cik"], x["fiscal_year"], x["category_id"]) for x in quotes}
    require(assignments == support and len(assignments) == 467 and len(quotes) == 606, "Practice support/panel mismatch")
    unit_by_id = {u["evidence_id"]: u for u in units}
    for quote in quotes:
        locations = p.exact_quote(quote["quote"], unit_by_id[quote["evidence_id"]])
        require(locations == json.loads(quote["quote_locations"]), "Practice quote locations differ")
    for stat in read_csv(ROOT / "outputs/summary_statistics/practices/practice_category_statistics.csv"):
        if stat["scope"] not in ["all", "fiscal_year"]:
            continue
        ps = panel if stat["scope"] == "all" else [x for x in panel if str(x["fiscal_year"]) == stat["scope_value"]]
        count = sum(x[stat["category_id"]] for x in ps)
        require(count == int(stat["firm_year_count"]) and len(ps) == int(stat["denominator"]), "Practice statistic mismatch")
        require(abs(100 * count / len(ps) - float(stat["percentage"])) < 1e-12, "Practice percentage mismatch")
    return primary, dict(native_panel=native_check, primary_panel=primary_check,
                         validated_evidence_units_n=len(units), exact_context_quote_rows_n=len(quotes),
                         practice_assignments_n=len(assignments), practice_statistics_match=True,
                         validation_scope="Original structural, category, status and continuous-context quote checks; no semantic accuracy claim")


def sample_smoke():
    g = load_frozen("governance")
    require(g.system() == (ROOT / "config/governance_prompts/system_prompt.txt").read_text(encoding="utf-8"), "Saved full system prompt differs from original builder")
    source_map = {(x["cik"], x["fiscal_year"], x["section"]): x for x in read_csv(ROOT / "data/sample/manifest.csv")}
    results = read_csv(ROOT / "data/sample/section_results.csv")
    payload_matches = 0
    labels = Counter()
    for row in results:
        src = source_map[row["cik"], row["fiscal_year"], row["section"]]
        path = ROOT / src["local_input_file"]
        require(sha(path) == row["input_sha256"], "Sample source hash differs")
        text = path.read_text(encoding="utf-8")
        g.validate(result_from_section(row), text)
        user = g.user(row, text)
        payload = g.build_payload(g.system(), user, max_tokens=g.MAX_TOKENS)
        require("thinking" not in payload and "reasoning_effort" not in payload and payload["temperature"] == 0, "Historical request configuration changed")
        # Preserve the historical serializer, including insertion order and spaces.
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
        if digest == row["request_payload_sha256"]:
            payload_matches += 1
        labels[row["classification"]] += 1
    require(payload_matches == len(results), "Sample historical request payload hashes differ")
    p, _ = load_frozen("practices")
    request = read_json(ROOT / "data/sample/practices_closed_request.json")
    codebook = read_json(ROOT / "config/practices_prompts/codebook.json")
    units = read_json(PDATA / "native/evidence_units.json")
    unit = next(u for u in units if u["evidence_id"] == "0000004962_FY2020_item7_E01")
    runtime_user = (ROOT / "config/practices_prompts/runtime_user_prompt_template.txt").read_text(encoding="utf-8").format(
        codebook_json=p.canonical(codebook), evidence_unit_json=p.canonical(p.unit_input(unit)))
    practice_payload = p.build_payload(p.prompt.CODING_SYSTEM, runtime_user, max_tokens=16384)
    require(practice_payload == request["payload"], "Saved Practice request differs from runtime builder")
    require(p.digest(p.canonical(practice_payload).encode()) == request["payload_sha256"], "Saved Practice request hash differs")
    require(p.prompt.CODING_SYSTEM == (ROOT / "config/practices_prompts/system_prompt.txt").read_text(encoding="utf-8"), "Practice system snapshot differs")
    return dict(source_sections_n=len(results), source_hashes_match=True,
                source_quote_and_schema_validation=True, saved_system_prompt_matches_builder=True,
                historical_request_payloads_built_without_network=len(results),
                exact_original_payload_hash_matches=payload_matches,
                practices_saved_request_matches_runtime_builder=True,
                practices_runtime_template_verified_against_saved_request=True,
                label_counts=dict(labels), paid_inference_executed=False)


def copied_file_integrity(source_project=None):
    records = read_json(ROOT / "outputs/validation/assembly_records.json")
    mismatches = []
    original_changes = []
    for item in records:
        path = ROOT / item["prototype_path"]
        if not path.is_file() or sha(path) != item["prototype_sha256"]:
            mismatches.append(item["prototype_path"])
        if source_project:
            for relative, expected in zip(json.loads(item["original_relative_path"]), json.loads(item["source_sha256"])):
                original = source_project / relative
                if not original.is_file() or sha(original) != expected:
                    original_changes.append(relative)
    require(not mismatches, "Copied/derived files differ from assembly records: " + repr(mismatches[:8]))
    require(not original_changes, "Original source hashes changed: " + repr(original_changes[:8]))
    return dict(assembled_files_checked=len(records), mismatches=[],
                original_source_hashes_checked=bool(source_project), original_source_changes=[])


def sealed_file_integrity():
    manifest = ROOT / "docs/delivery_manifest.json"
    if not manifest.is_file():
        return dict(status="not yet sealed during assembly")
    artifacts = read_json(manifest)["files"]
    bad = [p for p, expected in artifacts.items() if not (ROOT / p).is_file() or sha(ROOT / p) != expected]
    require(not bad, "Sealed prototype files differ: " + repr(bad[:8]))
    return dict(status="passed", files_checked=len(artifacts), mismatches=[])


def credential_scan():
    findings = []
    checked = 0
    token = os.getenv("DEEPSEEK_API_KEY", "").encode()
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {"tmp", "__pycache__", ".venv", ".git"} for part in path.relative_to(ROOT).parts):
            continue
        data = path.read_bytes()
        checked += 1
        if path.name == ".env" or re.search(rb"\bsk-[A-Za-z0-9_-]{20,}\b", data) or re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", data) or (token and token in data):
            findings.append(path.relative_to(ROOT).as_posix())
    require(not findings, "Potential credentials in artifact: " + repr(findings))
    return dict(files_scanned=checked, credential_value_findings=[])


def replay_output(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    require(path.is_relative_to(ROOT / "outputs/reproduced"), "Replay output must be within prototype/outputs/reproduced")
    path.mkdir(parents=True, exist_ok=True)
    return path
