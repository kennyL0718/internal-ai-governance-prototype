"""Resumable, evidence-checked semantic coding of saved Item 1A candidates."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .item1a_candidate_pipeline import ROOT, read_csv
from .item1a_multiyear import SAMPLE, year_output
from .llm.client import BASE_URL, INTENDED_MODEL_VERSION, MODEL, PROVIDER, chat_json, credential_detected, load_config, smoke_test
from .llm.semantic_prompt import PROMPT_VERSION, SYSTEM_PROMPT

BASE = ROOT / "outputs/fy2020_2025_item1a_ai_restriction_panel"
OUT = BASE / "semantic_v1"
CRITERIA = ROOT / "docs/AI use restrictions.md"
CLASSES = {"positive", "concern_only", "ambiguous", "not_relevant"}
NATURES = {"mandatory_constraint", "descriptive_practice", "unclear", "not_applicable"}
MECHANISMS = {"prohibition", "approved_tools_only", "prior_approval", "data_restriction", "purpose_restriction", "access_restriction", "deployment_restriction", "mandatory_human_review", "mandatory_validation", "mandatory_risk_assessment", "mandatory_monitoring", "mandatory_governance_control", "other"}
RESULT_FIELDS = ["company", "ticker", "fiscal_year", "risk_factor_heading", "ai_related", "classification", "restriction_type", "constraint_nature", "restricted_actor", "restricted_behavior", "restriction_mechanism", "evidence_sentence", "reasoning_summary", "manual_review", "reason_for_review"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _review_requested(value: bool | int | str) -> bool:
    return str(value).strip().lower() in {"true", "1"}


def _restriction_value(row: dict) -> str:
    """CSV-safe restriction value: an empty cell means unresolved."""
    if row["classification"] == "positive":
        return "1"
    if row["classification"] == "ambiguous" and _review_requested(row["manual_review"]):
        return ""
    return "0"


def _firm_year_decision(passage_rows: list[dict], *, missing: bool = False, complete: bool = True) -> tuple[str, str, bool]:
    """Aggregate only observed passages; incomplete nonpositives stay unresolved."""
    review = missing or any(_review_requested(r["manual_review"]) or _review_requested(r.get("qc_manual_review", False)) for r in passage_rows)
    if missing:
        return "unresolved_missing_item1a", "", review
    if any(r["classification"] == "positive" for r in passage_rows):
        return "positive", "1", True
    if not complete:
        return "partial_candidate_coverage", "", review
    if any(_restriction_value(r) == "" for r in passage_rows):
        return "ambiguous", "", True
    if any(r["classification"] == "ambiguous" for r in passage_rows):
        return "ambiguous", "0", review
    if any(r["classification"] == "concern_only" for r in passage_rows):
        return "concern_only", "0", review
    return "not_relevant", "0", review


def _load() -> tuple[list[dict], list[dict], dict]:
    sample = read_csv(SAMPLE)
    old_panel = read_csv(BASE / "firm_year_panel.csv")
    if len(sample) != 55 or len({r["ticker"] for r in sample}) != 55 or len(old_panel) != 330:
        raise ValueError("Fixed 55-firm, 330-firm-year universe is incomplete")
    old_by_key = {(r["ticker"], r["fiscal_year"]): r for r in old_panel}
    if len(old_by_key) != 330:
        raise ValueError("Duplicate firm-year in old panel")
    old_passages = {(r["ticker"], r["fiscal_year"], r["candidate_id"]): r for r in read_csv(BASE / "candidate_review_audit.csv")}
    candidates = []
    for year in range(2020, 2026):
        for row in read_csv(year_output(year) / "ai_candidate_passages.csv"):
            key = (row["ticker"], str(year), row["candidate_id"])
            if key not in old_passages:
                raise ValueError(f"Old coding missing: {key}")
            row = dict(row, fiscal_year=str(year), old_passage=old_passages[key])
            candidates.append(row)
    if len(candidates) != len(old_passages):
        raise ValueError("Saved candidate count differs from old passage audit")
    return candidates, old_panel, old_by_key


def _pilot(candidates: list[dict]) -> list[dict]:
    """Deterministic 25-case calibration with all old positives and ambiguities."""
    ordered = sorted(candidates, key=lambda r: (r["fiscal_year"], r["ticker"], r["candidate_id"]))
    selected = [r for r in ordered if r["old_passage"]["AI_restriction"] == "1" or r["old_passage"]["ambiguous"] == "1"]
    extras = [r for r in ordered if r not in selected]
    # Diverse fiscal years, with prior AI concerns and non-concern cases.
    for year in range(2020, 2026):
        for concern in ("1", "0"):
            match = next((r for r in extras if r["fiscal_year"] == str(year) and r["old_passage"]["concern_only"] == concern), None)
            if match is not None and len(selected) < 25:
                selected.append(match)
                extras.remove(match)
    for row in extras:
        if len(selected) >= 25:
            break
        selected.append(row)
    return selected


def _frozen_pilot(candidates: list[dict]) -> list[dict]:
    path = OUT / "pilot_manifest.csv"
    if not path.is_file():
        return _pilot(candidates)
    manifest = read_csv(path)
    selected_ids = [(r["fiscal_year"], r["ticker"], r["candidate_id"]) for r in manifest]
    if len(selected_ids) != 25 or len(set(selected_ids)) != 25:
        raise ValueError("Frozen pilot manifest must have 25 unique passages")
    by_id = {(r["fiscal_year"], r["ticker"], r["candidate_id"]): r for r in candidates}
    if any(key not in by_id for key in selected_ids):
        raise ValueError("Frozen pilot contains a passage absent from saved candidates")
    return [by_id[key] for key in selected_ids]


def _payload(row: dict) -> str:
    # Saved candidate_text is the risk-factor cluster; surrounding_context
    # provides adjacent text when it is not already included.
    context = row["candidate_text"]
    adjacent = row.get("surrounding_context", "")
    if adjacent and _normal(adjacent) not in _normal(context):
        context += "\n\nADJACENT ITEM 1A CONTEXT:\n" + adjacent
    return json.dumps({"company": row["company_name"], "ticker": row["ticker"], "fiscal_year": row["fiscal_year"], "risk_factor_heading": row["subsection_heading"], "item1a_passage": context}, ensure_ascii=False)


def _config() -> dict:
    return {"provider": PROVIDER, "model": MODEL, "intended_model_version": INTENDED_MODEL_VERSION, "base_url": BASE_URL, "api_key_present": credential_detected(_env_file())}


def _env_file() -> Path:
    """Prefer the repository .env; accept the enclosing workspace .env."""
    local = ROOT / ".env"
    return local if local.is_file() else ROOT.parent / ".env"


def _validate(result: dict, row: dict) -> dict:
    if not isinstance(result, dict) or not set(RESULT_FIELDS).issubset(result):
        raise ValueError("LLM output has missing required keys")
    if str(result["ticker"]).upper() != row["ticker"] or str(result["fiscal_year"]) != row["fiscal_year"]:
        raise ValueError("LLM output has wrong firm-year")
    if result["classification"] not in CLASSES or result["constraint_nature"] not in NATURES:
        raise ValueError("LLM output has invalid classification or constraint nature")
    mechanisms = result["restriction_mechanism"]
    if not isinstance(mechanisms, list) or not set(mechanisms) <= MECHANISMS:
        raise ValueError("LLM output has invalid restriction mechanism")
    evidence = str(result["evidence_sentence"]).strip()
    source = _normal(row["candidate_text"] + " " + row.get("surrounding_context", ""))
    if evidence and _normal(evidence) not in source:
        raise ValueError("Evidence sentence is absent from saved Item 1A passage")
    positive = result["classification"] == "positive"
    if positive:
        if result["restriction_type"] not in ("R1", "R2") or result["constraint_nature"] != "mandatory_constraint" or not all((result["restricted_actor"], result["restricted_behavior"], mechanisms, evidence)):
            raise ValueError("Positive lacks concrete actor, behavior, mechanism, mandatory nature or original evidence")
    elif result["restriction_type"] != "none":
        raise ValueError("Non-positive has restriction type")
    if not isinstance(result["ai_related"], bool) or not isinstance(result["manual_review"], bool):
        raise ValueError("Boolean fields have wrong type")
    if positive and not result["ai_related"]:
        raise ValueError("Positive cannot be unrelated to AI")
    if positive and not result["manual_review"]:
        raise ValueError("Every preliminary positive must enter manual review")
    if result["classification"] == "ambiguous" and not result["manual_review"] and not evidence:
        raise ValueError("Governance ambiguous needs an exact source quote")
    if result["manual_review"] and not str(result["reason_for_review"]).strip():
        raise ValueError("Manual review requires a reason")
    if not str(result["reasoning_summary"]).strip():
        raise ValueError("Classification requires a rationale")
    return result


def _cache_path(row: dict, system: str, config: dict) -> Path:
    identity = json.dumps([PROMPT_VERSION, _hash(system.encode()), config["provider"], config["model"], _payload(row)], ensure_ascii=False).encode()
    return OUT / "cache" / f"FY{row['fiscal_year']}_{row['ticker']}_{row['candidate_id']}_{_hash(identity)[:20]}.json"


def _checked_record(record: dict, row: dict) -> dict:
    """Preserve raw paid output in cache; flag imperfect nonpositive quotes."""
    checked = dict(record)
    result = dict(record["result"])
    evidence = str(result.get("evidence_sentence", "")).strip()
    source = _normal(row["candidate_text"] + " " + row.get("surrounding_context", ""))
    checked["evidence_validation"] = "exact_source_match" if evidence and _normal(evidence) in source else "no_evidence" if not evidence else "source_quote_mismatch_review"
    if checked["evidence_validation"] == "source_quote_mismatch_review":
        result["classification"] = "ambiguous"
        result["restriction_type"] = "none"
        result["constraint_nature"] = "unclear"
        result["restriction_mechanism"] = []
        result["evidence_sentence"] = ""
        result["manual_review"] = True
        existing = str(result.get("reason_for_review", "")).strip()
        result["reason_for_review"] = (existing + " | " if existing else "") + "Model evidence was not an exact contiguous Item 1A quote; verify the original passage."
    _validate(result, row)
    checked["result"] = result
    return checked


def _classify(row: dict, system: str, config: dict) -> dict:
    path = _cache_path(row, system, config)
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        cached["cache_status"] = "hit"
        return _checked_record(cached, row)
    result, call_metadata = chat_json(system, _payload(row), config=load_config(_env_file()))
    record = {"result": result, **call_metadata, "prompt_version": PROMPT_VERSION, "criteria_sha256": _hash(CRITERIA.read_bytes()), "candidate_sha256": _hash(row["candidate_text"].encode()), "observation_id": f"FY{row['fiscal_year']}_{row['candidate_id']}", "classified_at_utc": _now(), "retries": call_metadata["retry_count"]}
    _write_json(path, record)
    # Persist a paid response even when evidence/schema validation fails, so
    # reruns do not unknowingly purchase the same observation again.
    return _checked_record(record, row)


def _aggregate(rows: list[dict], old_panel: list[dict], old_by_key: dict, complete: bool,
               *, full_text_coverage: bool = True, failures: list[dict] | None = None) -> None:
    failures = failures or []
    failed_by_firm = defaultdict(list)
    for failure in failures:
        failed_by_firm[(failure["ticker"], failure["fiscal_year"])].append(failure)
    by_firm = defaultdict(list)
    for row in rows:
        by_firm[(row["ticker"], row["fiscal_year"])].append(row)
    panel, comparison, queue = [], [], []
    for old in old_panel:
        key = (old["ticker"], old["fiscal_year"])
        if not complete and key not in by_firm:
            continue
        passage_rows = by_firm[key]
        expected = int(old["candidate_count"])
        if not complete and expected != len(passage_rows):
            continue
        if complete and full_text_coverage and expected != len(passage_rows):
            raise ValueError(f"Incomplete candidate coverage for {key}: {len(passage_rows)}/{expected}")
        missing = old["item1a_extraction_status"] != "success"
        candidate_complete = expected == len(passage_rows) and not failed_by_firm[key]
        coverage_complete = full_text_coverage and candidate_complete
        pos = [r for r in passage_rows if r["classification"] == "positive"]
        review = [r for r in passage_rows if _review_requested(r["manual_review"]) or _review_requested(r.get("qc_manual_review", False))]
        new, value, needs_review = _firm_year_decision(passage_rows, missing=missing, complete=coverage_complete)
        coverage_reason = "" if missing or coverage_complete else (
            "Saved AI-anchor candidates do not establish complete Item 1A negative coverage."
            if candidate_complete else "One or more saved candidates failed v2.1 classification.")
        needs_review = needs_review or bool(coverage_reason)
        evidence = " | ".join(r["evidence_sentence"] for r in pos)
        mechanisms = sorted({m for r in pos for m in json.loads(r["restriction_mechanism"])})
        record = {"company": old["company_name"], "ticker": key[0], "fiscal_year": key[1], "new_llm_classification": new, "AI_restriction": value, "R1": int(any(r["restriction_type"] == "R1" for r in pos)), "R2": int(any(r["restriction_type"] == "R2" for r in pos)), "evidence_sentence": evidence, "restriction_mechanism": json.dumps(mechanisms), "manual_review": int(needs_review), "candidate_count": expected, "coded_passage_count": len(passage_rows), "item1a_extraction_status": old["item1a_extraction_status"]}
        if not full_text_coverage:
            record.update({"candidate_coverage_complete": int(candidate_complete),
                           "full_item1a_negative_coverage": 0,
                           "unresolved_passage_count": len(failed_by_firm[key]) + sum(_restriction_value(r) == "" for r in passage_rows),
                           "coverage_review_reason": coverage_reason})
        panel.append(record)
        old_value = old["AI_restriction"]
        old_class = "positive" if old_value == "1" else "ambiguous" if old["review_status"] == "ambiguous_manual_review" else "unresolved_missing_item1a" if old_value == "" else "concern_only" if old["concern_only"] == "1" else "not_relevant"
        changed = old_class != new
        comparison.append({"company": record["company"], "ticker": key[0], "fiscal_year": key[1], "old_classification": old_class, "new_llm_classification": new, "old_ai_restriction": old_value, "new_ai_restriction": value, "changed": int(changed), "evidence_sentence": evidence, "reason_for_change": " | ".join(r["reasoning_summary"] for r in passage_rows) if changed else "", "manual_review": record["manual_review"]})
        for r in review:
            queue.append({"company": record["company"], "ticker": key[0], "fiscal_year": key[1], "heading": r["risk_factor_heading"], "original_passage": r["original_passage"], "evidence_sentence": r["evidence_sentence"], "proposed_classification": r["classification"], "reasoning_summary": r["reasoning_summary"], "reason_for_review": r["reason_for_review"], "candidate_id": r.get("candidate_id", ""), "restriction_type": r["restriction_type"], "review_category": "preliminary_positive" if r["classification"] == "positive" else "classification_uncertainty" if _restriction_value(r) == "" else "passage_quality"})
        if coverage_reason:
            queue.append({"company": record["company"], "ticker": key[0], "fiscal_year": key[1], "heading": "", "original_passage": "", "evidence_sentence": evidence, "proposed_classification": new, "reasoning_summary": "", "reason_for_review": coverage_reason, "candidate_id": "", "restriction_type": "", "review_category": "coverage_uncertainty"})
        for failure in failed_by_firm[key]:
            queue.append({"company": record["company"], "ticker": key[0], "fiscal_year": key[1], "heading": failure.get("heading", ""), "original_passage": failure.get("original_passage", ""), "evidence_sentence": "", "proposed_classification": "unresolved_failed_passage", "reasoning_summary": "", "reason_for_review": f"{failure['candidate_id']}: {failure['error']}", "candidate_id": failure["candidate_id"], "restriction_type": "", "review_category": "api_failure"})
        if missing:
            queue.append({"company": record["company"], "ticker": key[0], "fiscal_year": key[1], "heading": "", "original_passage": "", "evidence_sentence": "", "proposed_classification": new, "reasoning_summary": "", "reason_for_review": old["classification_reason"], "candidate_id": "", "restriction_type": "", "review_category": "missing_item1a"})
    prefix = "" if complete else "pilot_"
    _write_csv(OUT / f"{prefix}firm_year_panel.csv", panel, list(panel[0]) if panel else [])
    _write_csv(OUT / f"{prefix}old_vs_llm_comparison.csv", comparison, list(comparison[0]) if comparison else [])
    _write_csv(OUT / f"{prefix}manual_review_queue.csv", queue, ["company", "ticker", "fiscal_year", "heading", "original_passage", "evidence_sentence", "proposed_classification", "reasoning_summary", "reason_for_review"] + (["candidate_id", "restriction_type", "review_category"] if not full_text_coverage else []))
    counts = Counter(r["new_llm_classification"] for r in panel)
    disagreements = Counter(f"{r['old_classification']} -> {r['new_llm_classification']}" for r in comparison if r["changed"])
    completed = [r for r in comparison if r["old_classification"] != "unresolved_missing_item1a" and r["new_llm_classification"] != "unresolved_missing_item1a"]
    agreement = sum(not int(r["changed"]) for r in completed) / len(completed) if completed else 0
    report = [f"# {'Full run' if complete else 'Pilot'}: semantic AI use restriction coding", "", f"Criteria SHA-256: `{_hash(CRITERIA.read_bytes())}`; prompt: `{PROMPT_VERSION}`.", f"Provider: `{_config()['provider']}`; model: `{_config()['model']}`.", f"{'Firm-years' if complete else 'Complete firm-year subset'}: {len(panel)}; firm-years with AI passages: {sum(int(r['candidate_count']) > 0 for r in panel)}; passages coded: {len(rows)}.", f"Complete-firm-year subset only — positive: {counts['positive']}; R1: {sum(r['R1'] for r in panel)}; R2: {sum(r['R2'] for r in panel)}; concern only: {counts['concern_only']}; ambiguous: {counts['ambiguous']}. Partial firm-years are excluded from this aggregation.", f"Old/new exact-class agreement among available complete firm-years: {agreement:.2%}; changed: {sum(int(r['changed']) for r in comparison)}.", "", "## Disagreement categories", ""]
    if not full_text_coverage:
        report[5] = (f"Saved-candidate coding — preliminary positive: {counts['positive']}; "
                     f"partial Item 1A negative coverage: {counts['partial_candidate_coverage']}; "
                     f"missing Item 1A: {counts['unresolved_missing_item1a']}; "
                     f"failed passages: {len(failures)}. Only positive evidence can yield a provisional firm-year 1; "
                     "candidate-only nonpositives remain unresolved, never 0.")
        report[6] = "Historical comparison is descriptive only and does not determine v2.1 classifications."
    report += [f"- {category}: {count}" for category, count in disagreements.most_common()] or ["- None"]
    report += ["", "## Selected changes", ""]
    for r in [x for x in comparison if x["changed"]][:10]:
        report.append(f"- FY{r['fiscal_year']} {r['ticker']}: {r['old_classification']} -> {r['new_llm_classification']}; evidence: {r['evidence_sentence']}; reason: {r['reason_for_change']}")
    report += ["", "Missing Item 1A remains unresolved and is never coded as a negative."]
    (OUT / ("run_report.md" if complete else "pilot_report.md")).write_text("\n".join(report) + "\n", encoding="utf-8")


def _pilot_review(rows: list[dict], candidates: list[dict]) -> None:
    """Review all 25 passage observations, including partial firm-years."""
    old = {(r["fiscal_year"], r["ticker"], r["candidate_id"]): r["old_passage"] for r in candidates}
    comparison, queue = [], []
    for row in rows:
        prior = old[(row["fiscal_year"], row["ticker"], row["candidate_id"])]
        old_class = "positive" if prior["AI_restriction"] == "1" else "ambiguous" if prior["ambiguous"] == "1" else "concern_only" if prior["concern_only"] == "1" else "not_relevant"
        new_class = row["classification"]
        comparison.append({"company": row["company"], "ticker": row["ticker"], "fiscal_year": row["fiscal_year"], "candidate_id": row["candidate_id"], "old_classification": old_class, "new_llm_classification": new_class, "old_ai_restriction": prior["AI_restriction"], "new_ai_restriction": _restriction_value(row), "changed": int(old_class != new_class), "evidence_sentence": row["evidence_sentence"], "reason_for_change": row["reasoning_summary"] if old_class != new_class else "", "manual_review": int(bool(row["manual_review"] or row["qc_manual_review"])), "evidence_validation": row["evidence_validation"]})
        if row["manual_review"] or row["qc_manual_review"]:
            reason = " | ".join(filter(None, [row["reason_for_review"], row["qc_reason"]]))
            queue.append({"company": row["company"], "ticker": row["ticker"], "fiscal_year": row["fiscal_year"], "candidate_id": row["candidate_id"], "heading": row["risk_factor_heading"], "original_passage": row["original_passage"], "evidence_sentence": row["evidence_sentence"], "proposed_classification": new_class, "reasoning_summary": row["reasoning_summary"], "reason_for_review": reason})
    _write_csv(OUT / "pilot_passage_comparison.csv", comparison, list(comparison[0]))
    _write_csv(OUT / "pilot_manual_review_queue.csv", queue, ["company", "ticker", "fiscal_year", "candidate_id", "heading", "original_passage", "evidence_sentence", "proposed_classification", "reasoning_summary", "reason_for_review"])
    counts = Counter(r["classification"] for r in rows)
    shifts = Counter(f"{r['old_classification']} -> {r['new_llm_classification']}" for r in comparison if r["changed"])
    positive = [r for r in rows if r["classification"] == "positive"]
    spg = [r for r in rows if r["ticker"] == "SPG"]
    usage = {name: sum(json.loads(r["token_usage"]).get(name, 0) for r in rows) for name in ("prompt_tokens", "completion_tokens", "total_tokens")}
    report = ["# Calibration review: 25 saved Item 1A passages", "", f"Provider: {PROVIDER}; API model: `{MODEL}`; intended version: {INTENDED_MODEL_VERSION}; prompt: `{PROMPT_VERSION}`; criteria SHA-256: `{_hash(CRITERIA.read_bytes())}`.", f"Coverage: {len(rows)} passages across {len({(r['ticker'], r['fiscal_year']) for r in rows})} firm-years; the complete-firm-year pilot subset has {len(read_csv(OUT / 'pilot_firm_year_panel.csv'))} rows.", f"Passage labels: positive {counts['positive']}; concern_only {counts['concern_only']}; ambiguous {counts['ambiguous']}; not_relevant {counts['not_relevant']}.", f"Mandatory constraints: {sum(r['constraint_nature'] == 'mandatory_constraint' for r in rows)}; descriptive practices: {sum(r['constraint_nature'] == 'descriptive_practice' for r in rows)}.", f"Manual-review passages: {len(queue)}; source-quote mismatches: {sum(r['evidence_validation'] == 'source_quote_mismatch_review' for r in rows)}; API responses cached: {len(rows)}; failures: 0.", f"API-reported pilot token usage: {usage}.", f"Old/new passage-label changes: {sum(r['changed'] for r in comparison)} of {len(rows)}; old positive retained: {sum(r['old_classification'] == 'positive' and r['new_llm_classification'] == 'positive' for r in comparison)} of {sum(r['old_classification'] == 'positive' for r in comparison)}; old nonpositive to new positive: {sum(r['old_classification'] != 'positive' and r['new_llm_classification'] == 'positive' for r in comparison)}.", "", "## Label changes", ""]
    report += [f"- {label}: {count}" for label, count in shifts.most_common()] or ["- None"]
    report += ["", "## Positive evidence", ""]
    report += [f"- FY{r['fiscal_year']} {r['ticker']} {r['restriction_type']}: {r['evidence_sentence']}" for r in positive] or ["- None"]
    report += ["", "## Reviewed-use-case calibration", ""]
    report += [f"- FY{r['fiscal_year']} SPG: {r['classification']} ({r['constraint_nature']}); model did not infer mandatory approval or purpose restriction from the observed review sentence." for r in spg]
    report += ["", "The two SPG years have different nonpositive sublabels for the same reviewed-use-case sentence. Both are in the manual-review queue for subtype consistency.", "FY2025 CRVL moved from old positive to ambiguous because the policy reference does not identify the concrete prohibited behavior with enough precision; it remains in manual review.", "The two not_relevant to concern_only changes affect the AI-concern subtype, not the restriction indicator.", "The existing firm-year pilot panel contains only observations for which all saved candidate passages were included in this calibration. Use the passage comparison for all 25 observations.", "The five imperfect model quotes were removed from the derived evidence field and queued for review; their original API responses remain in cache. No model response was purchased twice.", ""]
    (OUT / "pilot_calibration_review.md").write_text("\n".join(report), encoding="utf-8")


def run(stage: str) -> None:
    if stage == "smoke":
        metadata = smoke_test(load_config(_env_file()))
        _write_json(OUT / "smoke_status.json", {**metadata, "structured_json_parsing_successful": True, "completed_at_utc": _now()})
        print(f"HTTP/API call successful; provider={PROVIDER}; returned model={metadata['returned_model']}; structured JSON parsing successful; token usage={metadata['token_usage']}")
        return
    candidates, old_panel, old_by_key = _load()
    criteria = CRITERIA.read_text(encoding="utf-8-sig")
    system = SYSTEM_PROMPT.format(criteria=criteria)
    config = _config()
    chosen = _frozen_pilot(candidates)
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / "pilot_manifest.csv").is_file():
        _write_csv(OUT / "pilot_manifest.csv", [{"company": r["company_name"], "ticker": r["ticker"], "fiscal_year": r["fiscal_year"], "candidate_id": r["candidate_id"], "old_ai_restriction": r["old_passage"]["AI_restriction"], "old_ambiguous": r["old_passage"]["ambiguous"], "heading": r["subsection_heading"]} for r in chosen], ["company", "ticker", "fiscal_year", "candidate_id", "old_ai_restriction", "old_ambiguous", "heading"])
    _write_json(OUT / "run_metadata.json", {"status": "prepared" if stage == "preflight" else "running", "stage": stage, "prompt_version": PROMPT_VERSION, "criteria_sha256": _hash(CRITERIA.read_bytes()), "provider": config["provider"], "model": config["model"], "intended_model_version": config["intended_model_version"], "base_url": config["base_url"], "api_key_present": config["api_key_present"], "candidate_count": len(candidates), "pilot_count": len(chosen), "old_outputs_untouched": True, "updated_at_utc": _now()})
    if stage == "preflight":
        old_count = Counter("positive" if r["AI_restriction"] == "1" else "ambiguous" if r["review_status"] == "ambiguous_manual_review" else "missing" if r["AI_restriction"] == "" else "negative" for r in old_panel)
        (OUT / "preflight_report.md").write_text("\n".join([
            "# Semantic Item 1A preflight", "",
            f"Existing universe: {len(old_panel)} firm-years; saved AI candidate passages: {len(candidates)}; calibration pilot: {len(chosen)} passages.",
            f"Old panel baseline: {dict(old_count)}.",
            f"Provider: `{config['provider']}`; model configured: {bool(config['model'])}; API key present: {config['api_key_present']}.",
            f"Authoritative criteria SHA-256: `{_hash(CRITERIA.read_bytes())}`; prompt: `{PROMPT_VERSION}`.",
            "", "The project LLM client now implements a minimal DeepSeek OpenAI-compatible request. This preflight used the saved candidate pilot and made no model call or new classification.",
            "The prior SPG FY2024/FY2025 R2 decisions rely on the reviewed-use-cases sentence, which the new prompt explicitly treats as insufficient by itself for a positive decision. They remain old baseline values pending actual LLM adjudication.",
            "", "Execution requires `DEEPSEEK_API_KEY` in the process environment or local ignored `.env`. Run `python scripts/12_semantic_item1a.py --stage smoke` first, then `--stage pilot`. Inspect calibration evidence and errors before any separate full run.",
            "Original extraction, raw filings, and previous classifications remain unchanged. Missing Item 1A cannot be coded as a negative.", ""
        ]), encoding="utf-8")
        print(f"Prepared {len(chosen)} pilot passages from {len(candidates)} saved candidates. DEEPSEEK_API_KEY detected: {'yes' if config['api_key_present'] else 'no'}.")
        return
    if not config["api_key_present"]:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    if not (OUT / "smoke_status.json").is_file():
        raise RuntimeError("Complete the tiny API smoke test before calibration")
    if stage == "full":
        pilot_cache = [_cache_path(r, system, config) for r in chosen]
        if any(not p.is_file() for p in pilot_cache):
            raise RuntimeError("Complete the 25-passage pilot before full execution")
    selected = chosen if stage == "pilot" else candidates
    rows, failures, retries = [], [], 0
    for candidate in selected:
        try:
            record = _classify(candidate, system, config)
            retries += record["retries"]
            result = record["result"]
            rows.append({**result, "restriction_mechanism": json.dumps(result["restriction_mechanism"], ensure_ascii=False), "manual_review": int(result["manual_review"]), "ai_related": int(result["ai_related"]), "candidate_id": candidate["candidate_id"], "observation_id": record["observation_id"], "original_passage": candidate["candidate_text"], "adjacent_context": candidate.get("surrounding_context", ""), "source_file": candidate["source_file"], "evidence_page": candidate["evidence_page"], "evidence_validation": record["evidence_validation"], "provider": record["provider"], "model": record["model"], "intended_model_version": record["intended_model_version"], "returned_model": record["returned_model"], "request_status": record["request_status"], "cache_status": record["cache_status"], "token_usage": json.dumps(record["token_usage"]), "prompt_version": record["prompt_version"], "criteria_sha256": record["criteria_sha256"], "classified_at_utc": record["classified_at_utc"], "retries": record["retries"]})
        except Exception as exc:
            failures.append({"fiscal_year": candidate["fiscal_year"], "ticker": candidate["ticker"], "candidate_id": candidate["candidate_id"], "error": str(exc)})
    prefix = "" if stage == "full" else "pilot_"
    for row in rows:
        row["qc_manual_review"] = 0
        row["qc_reason"] = ""
    if stage == "pilot":
        spg = [r for r in rows if r["ticker"] == "SPG" and r["fiscal_year"] in ("2024", "2025")]
        if len(spg) == 2 and len({r["classification"] for r in spg}) > 1:
            for row in spg:
                row["qc_manual_review"] = 1
                row["qc_reason"] = "Same reviewed-use-case sentence received different nonpositive sublabels across FY2024 and FY2025."
    _write_csv(OUT / f"{prefix}passage_level_results.csv", rows, RESULT_FIELDS + ["candidate_id", "observation_id", "original_passage", "adjacent_context", "source_file", "evidence_page", "evidence_validation", "qc_manual_review", "qc_reason", "provider", "model", "intended_model_version", "returned_model", "request_status", "cache_status", "token_usage", "prompt_version", "criteria_sha256", "classified_at_utc", "retries"])
    _write_csv(OUT / f"{prefix}failures.csv", failures, ["fiscal_year", "ticker", "candidate_id", "error"])
    if not failures:
        _aggregate(rows, old_panel, old_by_key, stage == "full")
        if stage == "pilot":
            _pilot_review(rows, candidates)
        report_path = OUT / ("run_report.md" if stage == "full" else "pilot_report.md")
        with report_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\nModel call retries: {retries}; failed passages: 0; source-quote mismatches flagged for manual review: {sum(r['evidence_validation'] == 'source_quote_mismatch_review' for r in rows)}; unresolved missing Item 1A firm-years: {sum(r['item1a_extraction_status'] != 'success' for r in old_panel) if stage == 'full' else 'see full run'}.\n")
    _write_json(OUT / "run_metadata.json", {"status": "complete" if not failures else "incomplete", "stage": stage, "prompt_version": PROMPT_VERSION, "criteria_sha256": _hash(CRITERIA.read_bytes()), "provider": config["provider"], "model": config["model"], "intended_model_version": config["intended_model_version"], "base_url": config["base_url"], "candidate_count": len(candidates), "processed_count": len(rows), "failures": len(failures), "retries": retries, "updated_at_utc": _now()})
    print(f"{stage}: {len(rows)}/{len(selected)} passages coded; failures={len(failures)}; retries={retries}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("preflight", "smoke", "pilot", "full"), default="preflight")
    run(parser.parse_args().stage)
