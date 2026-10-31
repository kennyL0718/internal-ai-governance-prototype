"""FY2020-FY2024 reuse of the verified FY2025 Item 1A candidate-only protocol."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .item1a_candidate_pipeline import (
    AMBIGUOUS_FIELDS,
    CANDIDATE_FIELDS,
    CONFIG,
    EVIDENCE_FIELDS,
    FIRM_FIELDS,
    ROOT,
    VALID_CLASSES,
    _clusters,
    _heading,
    _page_label,
    _write_csv,
    compile_anchors,
    load_config,
    matched_terms,
    read_csv,
)
from .utils import AI_ADOPTION_PANEL_RELATIVE_PATH

HISTORICAL_MANIFEST = ROOT / "data/interim/documents/fy2020_fy2025_10k_manifest.csv"
SAMPLE = ROOT / "data/interim/samples/sample_55.csv"


def year_output(year: int) -> Path:
    if year not in range(2020, 2026):
        raise ValueError(f"Unsupported fiscal year: {year}")
    return ROOT / "outputs" / f"fy{year}_item1a_ai_adoption_review"


def year_manifest(year: int) -> dict[str, dict]:
    rows = [row for row in read_csv(HISTORICAL_MANIFEST) if row["fiscal_year"] == str(year)]
    if len(rows) != 55 or len({row["ticker"] for row in rows}) != 55:
        raise ValueError(f"FY{year} manifest must contain 55 unique tickers")
    return {row["ticker"]: row for row in rows}


def _extract_pair(blocks: list[dict]) -> tuple[int, int] | None:
    from .item1a_secondary_qa import locate
    result = locate(blocks)
    if result["extraction_status"] == "boundary_unresolved" or result["start"] is None:
        return None
    return result["start"], result["end"]


def extract_year(year: int) -> dict:
    """Extract Item 1A and printed-page maps without modifying source filings."""
    from .item1a_audit import page_map
    from .item1a_review import blocks as html_blocks

    out = year_output(year)
    audit_dir, page_dir, text_dir = out / "audit", out / "page_maps", out / "item1a_text"
    for directory in (audit_dir, page_dir, text_dir):
        directory.mkdir(parents=True, exist_ok=True)
    sample = read_csv(SAMPLE)
    manifest = year_manifest(year)
    extraction_rows = []
    structural_rows = []
    for company in sample:
        ticker = company["ticker"]
        meta = manifest[ticker]
        base = {
            "ticker": ticker,
            "source_file": meta.get("local_path", ""),
            "filing_date": meta.get("filing_date", ""),
            "fiscal_year": year,
        }
        if meta["download_status"] != "success" or not meta.get("local_path"):
            extraction_rows.append({**base, "extraction_status": "missing_10k", "word_count": "", "error": meta.get("failure_reason") or "10-K unavailable in fixed local set"})
            continue
        source = ROOT / meta["local_path"]
        if not source.is_file():
            extraction_rows.append({**base, "extraction_status": "missing_10k", "word_count": "", "error": "Manifest local_path is absent"})
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != meta["sha256"]:
            raise RuntimeError(f"Raw source hash changed: FY{year} {ticker}")
        all_blocks = html_blocks(source)
        pair = _extract_pair(all_blocks)
        if pair is None:
            extraction_rows.append({**base, "extraction_status": "extraction_failed", "word_count": "", "error": "Reliable Item 1A to Item 1B boundary not found"})
            continue
        start, end = pair
        section = all_blocks[start:end]
        words = sum(len(block["text"].split()) for block in section)
        status = "success" if words > 1500 and end < len(all_blocks) else "extraction_failed"
        error = "" if status == "success" else "Extracted section failed minimum-length or terminal-boundary gate"
        audit = {
            "ticker": ticker,
            "fiscal_year": year,
            "source_file": meta["local_path"],
            "sha256": meta["sha256"],
            "start_block": start,
            "end_block_exclusive": end,
            "start_heading": all_blocks[start]["text"],
            "end_heading": all_blocks[end]["text"] if end < len(all_blocks) else "",
            "word_count": words,
            "extraction_status": status,
            "blocks": section,
        }
        (audit_dir / f"{ticker}.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        extraction_rows.append({**base, "extraction_status": status, "word_count": words, "error": error})
        if status != "success":
            continue
        (text_dir / f"{ticker}_FY{year}_Item1A.txt").write_text("\n\n".join(block["text"] for block in section) + "\n", encoding="utf-8")
        _, mapped = page_map(source, all_blocks)
        selected = {str(index): mapped[index] for index in range(start, end)}
        page_data = {
            "ticker": ticker,
            "fiscal_year": year,
            "page_number_type": "printed",
            "mapping_method": "literal printed label in the same explicit HTML page segment/container; no interpolation",
            "start": mapped[start],
            "last": mapped[end - 1],
            "blocks": selected,
        }
        (page_dir / f"{ticker}.json").write_text(json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8")
        structural_rows.append({
            "ticker": ticker,
            "word_count": words,
            "start_block": start,
            "end_block_exclusive": end,
            "start_heading": all_blocks[start]["text"],
            "end_heading": all_blocks[end]["text"],
            "mapped_blocks": sum(value["printed_page"] is not None for value in selected.values()),
            "total_blocks": len(selected),
        })
    _write_csv(out / "extraction_manifest.csv", extraction_rows, ["ticker", "source_file", "filing_date", "fiscal_year", "extraction_status", "word_count", "error"])
    (audit_dir / "structural_validation.json").write_text(json.dumps(structural_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    status = {
        "fiscal_year": year,
        "expected_firms": 55,
        "source_files": sum(row["extraction_status"] != "missing_10k" for row in extraction_rows),
        "successful_extractions": sum(row["extraction_status"] == "success" for row in extraction_rows),
        "missing_10k": sum(row["extraction_status"] == "missing_10k" for row in extraction_rows),
        "extraction_failed": sum(row["extraction_status"] == "extraction_failed" for row in extraction_rows),
        "source_downloads": 0,
        "raw_documents_modified": 0,
    }
    (out / "extraction_run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def screen_year(year: int) -> dict:
    out = year_output(year)
    config = load_config(CONFIG)
    anchors = compile_anchors(config["anchor_terms"])
    options = config["candidate_construction"]
    sample = read_csv(SAMPLE)
    manifest = year_manifest(year)
    extraction = {row["ticker"]: row for row in read_csv(out / "extraction_manifest.csv")}
    candidates, screening = [], []
    for company in sample:
        ticker = company["ticker"]
        state = extraction[ticker]
        if state["extraction_status"] != "success":
            screening.append({"ticker": ticker, "extraction_status": state["extraction_status"], "candidate_count": 0, "extraction_error": state["error"]})
            continue
        audit = json.loads((out / "audit" / f"{ticker}.json").read_text(encoding="utf-8"))
        page_map = json.loads((out / "page_maps" / f"{ticker}.json").read_text(encoding="utf-8"))
        blocks = audit["blocks"]
        hits = [index for index, block in enumerate(blocks) if matched_terms(block["text"], anchors)]
        ticker_rows = []
        for number, group in enumerate(_clusters(hits, int(options["max_hit_gap_blocks"])), 1):
            start = max(0, group[0] - int(options["context_blocks_before"]))
            end = min(len(blocks), group[-1] + int(options["context_blocks_after"]) + 1)
            context_blocks = blocks[start:end]
            hit_blocks = [blocks[index] for index in group]
            terms = sorted({term for block in hit_blocks for term in matched_terms(block["text"], anchors)}, key=str.casefold)
            page, page_flag = _page_label([block["block"] for block in hit_blocks], page_map)
            ticker_rows.append({
                "company_name": company["company_name"],
                "ticker": ticker,
                "source_file": manifest[ticker]["local_path"],
                "candidate_id": f"{ticker}-C{number:02d}",
                "matched_terms": "; ".join(terms),
                "candidate_text": "\n\n".join(block["text"] for block in hit_blocks),
                "surrounding_context": "\n\n".join(block["text"] for block in context_blocks),
                "evidence_page": page,
                "subsection_heading": _heading(blocks, group[0]),
                "hit_blocks": json.dumps([block["block"] for block in hit_blocks]),
                "candidate_blocks": json.dumps([block["block"] for block in context_blocks]),
                "page_mapping_review_flag": page_flag,
            })
        candidates.extend(ticker_rows)
        screening.append({"ticker": ticker, "extraction_status": "success", "candidate_count": len(ticker_rows), "extraction_error": ""})
    _write_csv(out / "ai_candidate_passages.csv", candidates, CANDIDATE_FIELDS)
    _write_csv(out / "screening_status.csv", screening, ["ticker", "extraction_status", "candidate_count", "extraction_error"])
    status = {
        "fiscal_year": year,
        "candidate_passages": len(candidates),
        "firms_with_candidates": sum(int(row["candidate_count"]) > 0 for row in screening),
        "zero_anchor_firms": sum(row["extraction_status"] == "success" and int(row["candidate_count"]) == 0 for row in screening),
        "source_downloads": 0,
        "raw_documents_modified": 0,
    }
    (out / "screening_run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def _load_reviews(out: Path) -> dict[str, dict]:
    path = out / "candidate_reviews.jsonl"
    if not path.exists():
        return {}
    reviews = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        review = json.loads(line)
        if review["classification"] not in VALID_CLASSES:
            raise ValueError(f"Invalid classification at line {line_number}")
        reviews[review["candidate_id"]] = review
    return reviews


def aggregate_year(year: int) -> dict:
    out = year_output(year)
    config = load_config(CONFIG)
    categories = config["risk_categories"]
    sample = read_csv(SAMPLE)
    manifest = year_manifest(year)
    candidates = read_csv(out / "ai_candidate_passages.csv")
    screening = {row["ticker"]: row for row in read_csv(out / "screening_status.csv")}
    reviews = _load_reviews(out)
    candidate_ids = {row["candidate_id"] for row in candidates}
    if set(reviews) - candidate_ids:
        raise ValueError(f"FY{year} reviews without candidates: {sorted(set(reviews) - candidate_ids)}")
    by_ticker = {row["ticker"]: [] for row in sample}
    for candidate in candidates:
        by_ticker[candidate["ticker"]].append(candidate)
    firms, evidence, ambiguous = [], [], []
    for company in sample:
        ticker = company["ticker"]
        meta = manifest[ticker]
        state = screening[ticker]
        ticker_candidates = by_ticker[ticker]
        ticker_reviews = [reviews.get(candidate["candidate_id"]) for candidate in ticker_candidates]
        missing_reviews = [candidate["candidate_id"] for candidate, review in zip(ticker_candidates, ticker_reviews) if review is None]
        positives = [(candidate, review) for candidate, review in zip(ticker_candidates, ticker_reviews) if review and review["classification"] == "type_a"]
        ambiguities = [(candidate, review) for candidate, review in zip(ticker_candidates, ticker_reviews) if review and review["classification"] == "ambiguous"]
        risk_categories = []
        for _, review in positives:
            for category in review.get("risk_categories", []):
                if category not in categories:
                    raise ValueError(f"Unknown category {category}: FY{year} {ticker}")
                if category not in risk_categories:
                    risk_categories.append(category)
        extraction_status = state["extraction_status"]
        if extraction_status != "success":
            value, review_status, notes = "", "extraction_failed", f"{extraction_status}: {state['extraction_error']}"
        elif not ticker_candidates:
            value, review_status, notes = 0, "completed", "zero_ai_anchor"
        elif missing_reviews:
            value, review_status, notes = "", "ambiguous_manual_review", "Unreviewed candidates: " + ", ".join(missing_reviews)
        elif ambiguities:
            value, review_status, notes = "", "ambiguous_manual_review", "Ambiguous candidates require manual review."
        else:
            value, review_status, notes = int(bool(positives)), "completed", "Candidate-only semantic review completed."
        seen = set()
        for candidate, review in positives:
            if review.get("duplicate_of"):
                continue
            evidence_key = review.get("evidence_key") or candidate["candidate_id"]
            if evidence_key in seen:
                continue
            seen.add(evidence_key)
            blocks = review.get("evidence_blocks", [])
            if blocks:
                page_map = json.loads((out / "page_maps" / f"{ticker}.json").read_text(encoding="utf-8"))
                page, page_flag = _page_label(blocks, page_map)
            else:
                page, page_flag = candidate["evidence_page"], int(candidate["page_mapping_review_flag"] or 0)
            evidence.append({
                "ticker": ticker,
                "evidence_page": page,
                "risk_category": "; ".join(review.get("risk_categories", [])),
                "classification_reason": review["classification_reason"],
                "review_flag": 1 if page_flag else int(review.get("review_flag", 0)),
            })
        for candidate, review in ambiguities:
            row = {
                "ticker": ticker,
                "candidate_id": candidate["candidate_id"],
                "evidence_page": candidate["evidence_page"],
                "classification_reason": review["classification_reason"],
                "review_flag": 1,
            }
            ambiguous.append(row)
            evidence.append({
                "ticker": ticker,
                "evidence_page": candidate["evidence_page"],
                "risk_category": "",
                "classification_reason": review["classification_reason"],
                "review_flag": 1,
            })
        firms.append({
            "company_name": company["company_name"],
            "ticker": ticker,
            "sector": company["gics_sector"],
            "source_file": meta.get("local_path", ""),
            "filing_date": meta.get("filing_date", ""),
            "item1a_extraction_status": extraction_status,
            "ai_anchor_found": int(bool(ticker_candidates)),
            "candidate_count": len(ticker_candidates),
            "ai_adoption_concern_yes": value,
            "ai_risk_categories": "; ".join(risk_categories),
            "evidence_count": len(seen),
            "review_status": review_status,
            "review_notes": notes,
        })
    _write_csv(out / "firm_level_results.csv", firms, FIRM_FIELDS)
    _write_csv(out / "passage_level_evidence.csv", evidence, EVIDENCE_FIELDS)
    _write_csv(out / "ambiguous_review.csv", ambiguous, AMBIGUOUS_FIELDS)
    positives = [row for row in firms if str(row["ai_adoption_concern_yes"]) == "1"]
    negatives = [row for row in firms if str(row["ai_adoption_concern_yes"]) == "0"]
    manual = [row for row in firms if row["review_status"] != "completed"]
    evidence_by_ticker = Counter(row["ticker"] for row in evidence if row["risk_category"])
    page_labels_by_ticker = {}
    for company in sample:
        ticker = company["ticker"]
        path = out / "page_maps" / f"{ticker}.json"
        if not path.exists():
            page_labels_by_ticker[ticker] = set()
            continue
        mapping = json.loads(path.read_text(encoding="utf-8"))
        page_labels_by_ticker[ticker] = {
            str(value["printed_page"])
            for value in mapping["blocks"].values()
            if value["printed_page"] is not None
        }

    def evidence_page_is_mapped(row: dict) -> bool:
        label = row["evidence_page"]
        if not label:
            return bool(int(row["review_flag"]))
        endpoints = label.split("-", 1)
        return all(endpoint in page_labels_by_ticker[row["ticker"]] for endpoint in endpoints)

    checks = {
        "firm_count_exactly_55": len(firms) == 55 and len({row["ticker"] for row in firms}) == 55,
        "every_positive_has_evidence": all(evidence_by_ticker[row["ticker"]] >= 1 for row in positives),
        "evidence_count_matches": all(evidence_by_ticker[row["ticker"]] == int(row["evidence_count"]) for row in positives),
        "zero_anchor_has_no_type_a_evidence": all(not evidence_by_ticker[row["ticker"]] for row in firms if row["review_notes"] == "zero_ai_anchor"),
        "failed_not_zero": all(row["ai_adoption_concern_yes"] == "" for row in firms if row["item1a_extraction_status"] != "success"),
        "candidate_ids_unique": len(candidates) == len(candidate_ids),
        "candidate_reviews_complete": len(reviews) == len(candidates),
        "sample_ticker_sector_preserved": all(row["ticker"] == source["ticker"] and row["sector"] == source["gics_sector"] for row, source in zip(firms, sample)),
        "evidence_pages_in_source_map": all(evidence_page_is_mapped(row) for row in evidence),
    }
    assert all(checks.values()), checks
    checks["evidence_pages_missing"] = sum(not row["evidence_page"] for row in evidence)
    checks["duplicate_candidates_marked"] = sum(bool(review.get("duplicate_of")) for review in reviews.values())
    (out / "quality_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    category_counts = Counter(category for row in positives for category in row["ai_risk_categories"].split("; ") if category)
    report = [
        f"# FY{year} Item 1A AI Adoption Concerns Review", "",
        f"- Expected firms: 55",
        f"- Successfully extracted Item 1A: {sum(row['item1a_extraction_status'] == 'success' for row in firms)}",
        f"- Zero AI anchor firms: {sum(row['review_notes'] == 'zero_ai_anchor' for row in firms)}",
        f"- Firms with AI candidates: {sum(row['ai_anchor_found'] == 1 for row in firms)}",
        f"- Type A positive: {len(positives)}",
        f"- Negative: {len(negatives)}",
        f"- Manual review or missing: {len(manual)}", "",
        "## Type A risk categories", "",
    ]
    report.extend(f"- {category}: {count}" for category, count in category_counts.most_common())
    report.extend(["", "## Manual review", ""])
    report.extend(f"- {row['ticker']}: {row['review_notes']}" for row in manual)
    if not manual:
        report.append("- None.")
    (out / "review_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    status = {
        "protocol_version": config["version"],
        "fiscal_year": year,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": 55,
        "candidate_passages": len(candidates),
        "candidate_reviews": len(reviews),
        "positive": len(positives),
        "negative": len(negatives),
        "ambiguous_or_missing": len(manual),
        "source_downloads": 0,
        "raw_documents_modified": 0,
    }
    (out / "run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def build_panel() -> dict:
    panel_out = ROOT / AI_ADOPTION_PANEL_RELATIVE_PATH
    panel_out.mkdir(parents=True, exist_ok=True)
    expected_header = None
    panel_rows, audit_rows, duplicates = [], [], []
    seen = set()
    fy2025_source_rows = None
    for year in range(2020, 2026):
        path = year_output(year) / "firm_level_results.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            header = reader.fieldnames
        if expected_header is None:
            expected_header = header
        if header != expected_header:
            raise ValueError(f"FY{year} schema differs: {header} != {expected_header}")
        if year == 2025:
            fy2025_source_rows = rows
        for row in rows:
            key = (row["ticker"], year)
            if key in seen:
                duplicates.append({"ticker": row["ticker"], "fiscal_year": year, "reason": "duplicate key in annual result"})
                continue
            seen.add(key)
            panel = dict(row)
            panel["fiscal_year"] = year
            panel_rows.append(panel)
        reviews = _load_reviews(year_output(year))
        type_b = {candidate_id.split("-C", 1)[0] for candidate_id, review in reviews.items() if review["classification"] == "type_b"}
        type_c = {candidate_id.split("-C", 1)[0] for candidate_id, review in reviews.items() if review["classification"] == "type_c"}
        missing_10k = sum(row["item1a_extraction_status"] == "missing_10k" for row in rows)
        extraction_failure = sum(row["item1a_extraction_status"] == "extraction_failed" for row in rows)
        review_required = sum(row["review_status"] != "completed" for row in rows)
        audit_rows.append({
            "fiscal_year": year,
            "expected_firms": 55,
            "processed_firms": sum(row["review_status"] == "completed" for row in rows),
            "missing_firms": missing_10k,
            "missing_10k": missing_10k,
            "item1a_extraction_failure": extraction_failure,
            "processing_classification_failure": sum(row["review_status"] == "ambiguous_manual_review" for row in rows),
            "duplicate_firm_years": sum(item["fiscal_year"] == year for item in duplicates),
            "type_a_count": sum(row["ai_adoption_concern_yes"] == "1" for row in rows),
            "type_b_count": len(type_b),
            "type_c_count": len(type_c),
            "no_type_a_count": sum(row["ai_adoption_concern_yes"] == "0" for row in rows),
            "review_required_count": review_required,
            "annual_rows": len(rows),
        })
    panel_fields = expected_header[:2] + ["fiscal_year"] + expected_header[2:]
    audit_fields = list(audit_rows[0])
    _write_csv(panel_out / "firm_year_panel.csv", panel_rows, panel_fields)
    _write_csv(panel_out / "merge_audit.csv", audit_rows, audit_fields)
    _write_csv(panel_out / "duplicate_audit.csv", duplicates, ["ticker", "fiscal_year", "reason"])

    spot_checks = []
    rng = random.Random(42)
    for year in range(2020, 2025):
        annual_out = year_output(year)
        annual_firms = {row["ticker"]: row for row in read_csv(annual_out / "firm_level_results.csv")}
        annual_candidates = read_csv(annual_out / "ai_candidate_passages.csv")
        annual_reviews = _load_reviews(annual_out)
        eligible = [
            candidate for candidate in annual_candidates
            if annual_reviews[candidate["candidate_id"]]["classification"] == "type_a"
            and not annual_reviews[candidate["candidate_id"]].get("duplicate_of")
        ]
        candidate = rng.choice(eligible)
        ticker = candidate["ticker"]
        source = ROOT / candidate["source_file"]
        manifest_row = year_manifest(year)[ticker]
        extraction_audit = json.loads((annual_out / "audit" / f"{ticker}.json").read_text(encoding="utf-8"))
        audit_by_block = {block["block"]: block["text"] for block in extraction_audit["blocks"]}
        hit_blocks = json.loads(candidate["hit_blocks"])
        page_mapping = json.loads((annual_out / "page_maps" / f"{ticker}.json").read_text(encoding="utf-8"))
        mapped_labels = {
            str(value["printed_page"])
            for value in page_mapping["blocks"].values()
            if value["printed_page"] is not None
        }
        spot_checks.append({
            "fiscal_year": year,
            "ticker": ticker,
            "candidate_id": candidate["candidate_id"],
            "evidence_page": candidate["evidence_page"],
            "source_file": candidate["source_file"],
            "source_sha256_verified": int(hashlib.sha256(source.read_bytes()).hexdigest() == manifest_row["sha256"]),
            "candidate_blocks_match_extraction": int(all(block in audit_by_block for block in hit_blocks)),
            "evidence_page_mapped": int(all(endpoint in mapped_labels for endpoint in candidate["evidence_page"].split("-", 1))),
            "firm_classification_positive": int(annual_firms[ticker]["ai_adoption_concern_yes"] == "1"),
        })
    _write_csv(
        panel_out / "spot_check_audit.csv",
        spot_checks,
        ["fiscal_year", "ticker", "candidate_id", "evidence_page", "source_file", "source_sha256_verified", "candidate_blocks_match_extraction", "evidence_page_mapped", "firm_classification_positive"],
    )
    assert {row["fiscal_year"] for row in panel_rows} == set(range(2020, 2026))
    assert len(panel_rows) == sum(row["annual_rows"] for row in audit_rows)
    assert len(seen) == len(panel_rows)
    merged_2025 = [{key: value for key, value in row.items() if key != "fiscal_year"} for row in panel_rows if row["fiscal_year"] == 2025]
    assert merged_2025 == fy2025_source_rows
    type_domains_valid = all(
        isinstance(row["fiscal_year"], int)
        and row["ai_anchor_found"] in {"0", "1"}
        and row["candidate_count"].isdigit()
        and row["ai_adoption_concern_yes"] in {"", "0", "1"}
        and row["evidence_count"].isdigit()
        for row in panel_rows
    )
    categorical_domains_valid = all(
        row["item1a_extraction_status"] in {"success", "missing_10k", "extraction_failed"}
        and row["review_status"] in {"completed", "ambiguous_manual_review", "extraction_failed"}
        for row in panel_rows
    )
    assert type_domains_valid and categorical_domains_valid
    verification = {
        "years_present": sorted({row["fiscal_year"] for row in panel_rows}),
        "rows": len(panel_rows),
        "columns": len(panel_fields),
        "unique_firm_year": len(seen) == len(panel_rows),
        "duplicate_firm_years": len(duplicates),
        "annual_row_sum": sum(row["annual_rows"] for row in audit_rows),
        "fy2025_unchanged": merged_2025 == fy2025_source_rows,
        "csv_field_count": len(panel_fields),
        "utf8_bom": (panel_out / "firm_year_panel.csv").read_bytes().startswith(b"\xef\xbb\xbf"),
        "type_domains_valid": type_domains_valid,
        "categorical_domains_valid": categorical_domains_valid,
        "spot_checks": len(spot_checks),
        "spot_checks_all_passed": all(
            row["source_sha256_verified"]
            and row["candidate_blocks_match_extraction"]
            and row["evidence_page_mapped"]
            and row["firm_classification_positive"]
            for row in spot_checks
        ),
    }
    (panel_out / "panel_validation.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    return verification
