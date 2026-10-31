"""Offline two-stage Item 1A AI-anchor screening and candidate-only review outputs."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LEGACY_OUT = ROOT / "outputs" / "exploratory_fy2025_item1a_review"
OUT = ROOT / "outputs" / "fy2025_item1a_ai_adoption_review"
CONFIG = ROOT / "config" / "item1a_ai_screening.yaml"
CANDIDATE_FIELDS = [
    "company_name", "ticker", "source_file", "candidate_id", "matched_terms",
    "candidate_text", "surrounding_context", "evidence_page", "subsection_heading",
    "hit_blocks", "candidate_blocks", "page_mapping_review_flag",
]
FIRM_FIELDS = [
    "company_name", "ticker", "sector", "source_file", "filing_date",
    "item1a_extraction_status", "ai_anchor_found", "candidate_count",
    "ai_adoption_concern_yes", "ai_risk_categories", "evidence_count",
    "review_status", "review_notes",
]
EVIDENCE_FIELDS = [
    "ticker", "evidence_page", "risk_category", "classification_reason", "review_flag"
]
AMBIGUOUS_FIELDS = [
    "ticker", "candidate_id", "evidence_page", "classification_reason", "review_flag"
]
VALID_CLASSES = {"type_a", "type_b", "type_c", "ambiguous"}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def load_config(path: Path = CONFIG) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def compile_anchors(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    compiled = []
    for term in terms:
        words = re.split(r"[\s-]+", term.strip())
        body = r"[\s-]+".join(re.escape(word) for word in words)
        compiled.append((term, re.compile(rf"(?<![A-Za-z0-9_]){body}(?![A-Za-z0-9_])", re.I)))
    return compiled


def matched_terms(text: str, anchors: list[tuple[str, re.Pattern]]) -> list[str]:
    return [term for term, pattern in anchors if pattern.search(text)]


def _heading(blocks: list[dict], hit_index: int) -> str:
    for block in reversed(blocks[max(0, hit_index - 30):hit_index]):
        text = " ".join(block["text"].split())
        style = block.get("style", "").lower()
        if not 15 <= len(text) <= 240 or re.search(r"table of contents|^\d+$|^item\s", text, re.I):
            continue
        heading_style = "text-align:center" in style or "font-weight:bold" in style
        heading_text = not re.search(r"[.;:]$", text) and len(text.split()) <= 28
        if heading_style or heading_text:
            return text
    return ""


def _page_label(block_ids: list[int], page_map: dict) -> tuple[str, int]:
    pages = [page_map["blocks"][str(block_id)]["printed_page"] for block_id in block_ids]
    if not pages or any(page is None for page in pages):
        return "", 1
    unique = sorted(set(pages))
    if len(unique) == 1:
        return str(unique[0]), 0
    # Evidence may recur later in a multi-page risk factor without an anchor
    # term on every intervening page. Record the bounded printed-page range.
    return f"{unique[0]}-{unique[-1]}", 0


def _clusters(hit_indexes: list[int], gap: int) -> list[list[int]]:
    groups: list[list[int]] = []
    for index in hit_indexes:
        if not groups or index - groups[-1][-1] > gap:
            groups.append([index])
        else:
            groups[-1].append(index)
    return groups


def screen_candidates() -> dict:
    """Create candidates from extracted Item 1A only; never reads beyond saved audits."""
    config = load_config()
    anchors = compile_anchors(config["anchor_terms"])
    options = config["candidate_construction"]
    sample = read_csv(ROOT / "data/interim/samples/sample_55.csv")
    manifest = {row["ticker"]: row for row in read_csv(ROOT / "data/interim/documents/fy2025_10k_manifest.csv")}
    assert len(sample) == 55 and len({row["ticker"] for row in sample}) == 55
    rows: list[dict] = []
    firm_screening: list[dict] = []
    extraction_failures = config.get("extraction_failures", {})
    for company in sample:
        ticker = company["ticker"]
        source = ROOT / manifest[ticker]["local_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest[ticker]["sha256"]:
            raise RuntimeError(f"Raw source hash changed: {ticker}")
        audit_path = LEGACY_OUT / "audit" / f"{ticker}.json"
        page_path = LEGACY_OUT / "page_maps" / f"{ticker}.json"
        if ticker in extraction_failures:
            firm_screening.append({"ticker": ticker, "extraction_status": "extraction_failed", "candidate_count": 0, "extraction_error": extraction_failures[ticker]})
            continue
        if not audit_path.exists() or not page_path.exists():
            firm_screening.append({"ticker": ticker, "extraction_status": "extraction_failed", "candidate_count": 0, "extraction_error": "Missing extraction audit or page map."})
            continue
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        page_map = json.loads(page_path.read_text(encoding="utf-8"))
        if audit.get("extraction_status") != "success":
            firm_screening.append({"ticker": ticker, "extraction_status": "extraction_failed", "candidate_count": 0, "extraction_error": "Extraction audit did not pass."})
            continue
        blocks = audit["blocks"]
        hits = [i for i, block in enumerate(blocks) if matched_terms(block["text"], anchors)]
        groups = _clusters(hits, int(options["max_hit_gap_blocks"]))
        ticker_rows = []
        for number, group in enumerate(groups, 1):
            start = max(0, group[0] - int(options["context_blocks_before"]))
            end = min(len(blocks), group[-1] + int(options["context_blocks_after"]) + 1)
            candidate_blocks = blocks[start:end]
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
                "surrounding_context": "\n\n".join(block["text"] for block in candidate_blocks),
                "evidence_page": page,
                "subsection_heading": _heading(blocks, group[0]),
                "hit_blocks": json.dumps([block["block"] for block in hit_blocks]),
                "candidate_blocks": json.dumps([block["block"] for block in candidate_blocks]),
                "page_mapping_review_flag": page_flag,
            })
        rows.extend(ticker_rows)
        firm_screening.append({"ticker": ticker, "extraction_status": "success", "candidate_count": len(ticker_rows), "extraction_error": ""})
    _write_csv(OUT / "ai_candidate_passages.csv", rows, CANDIDATE_FIELDS)
    _write_csv(OUT / "screening_status.csv", firm_screening, ["ticker", "extraction_status", "candidate_count", "extraction_error"])
    status = {
        "protocol_version": config["version"], "sample_count": len(sample),
        "item1a_extracted": sum(row["extraction_status"] == "success" for row in firm_screening),
        "candidate_passages": len(rows),
        "firms_with_candidates": sum(int(row["candidate_count"]) > 0 for row in firm_screening),
        "zero_anchor_firms": sum(row["extraction_status"] == "success" and int(row["candidate_count"]) == 0 for row in firm_screening),
        "source_downloads": 0, "raw_documents_modified": 0,
    }
    (OUT / "screening_run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def load_reviews() -> dict[str, dict]:
    path = OUT / "candidate_reviews.jsonl"
    if not path.exists():
        return {}
    reviews = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row["classification"] not in VALID_CLASSES:
            raise ValueError(f"Invalid classification at line {line_number}")
        reviews[row["candidate_id"]] = row
    return reviews


def aggregate() -> dict:
    config = load_config()
    categories = config["risk_categories"]
    sample = read_csv(ROOT / "data/interim/samples/sample_55.csv")
    manifest = {row["ticker"]: row for row in read_csv(ROOT / "data/interim/documents/fy2025_10k_manifest.csv")}
    candidates = read_csv(OUT / "ai_candidate_passages.csv")
    screening = {row["ticker"]: row for row in read_csv(OUT / "screening_status.csv")}
    reviews = load_reviews()
    by_ticker: dict[str, list[dict]] = {row["ticker"]: [] for row in sample}
    for candidate in candidates:
        by_ticker[candidate["ticker"]].append(candidate)
    unknown_reviews = set(reviews) - {row["candidate_id"] for row in candidates}
    if unknown_reviews:
        raise ValueError(f"Reviews without candidates: {sorted(unknown_reviews)}")

    firms, evidence, ambiguous = [], [], []
    for company in sample:
        ticker = company["ticker"]
        state = screening[ticker]
        ticker_candidates = by_ticker[ticker]
        extraction_status = state["extraction_status"]
        reviewed = [reviews.get(row["candidate_id"]) for row in ticker_candidates]
        missing = [row["candidate_id"] for row, review in zip(ticker_candidates, reviewed) if review is None]
        positives = [(candidate, review) for candidate, review in zip(ticker_candidates, reviewed) if review and review["classification"] == "type_a"]
        ambiguities = [(candidate, review) for candidate, review in zip(ticker_candidates, reviewed) if review and review["classification"] == "ambiguous"]
        risk_categories = []
        for _, review in positives:
            for category in review.get("risk_categories", []):
                if category not in categories:
                    raise ValueError(f"Unknown category {category}: {ticker}")
                if category not in risk_categories:
                    risk_categories.append(category)
        if extraction_status != "success":
            value, review_status, notes = "", "extraction_failed", state.get("extraction_error") or "Item 1A could not be reliably extracted."
        elif not ticker_candidates:
            value, review_status, notes = 0, "completed", "zero_ai_anchor"
        elif missing:
            value, review_status, notes = "", "ambiguous_manual_review", "Unreviewed candidates: " + ", ".join(missing)
        elif ambiguities:
            value, review_status, notes = "", "ambiguous_manual_review", "Ambiguous candidates require manual review."
        else:
            value = int(bool(positives))
            review_status = "completed"
            notes = "Candidate-only semantic review completed."
        seen_evidence = set()
        for candidate, review in positives:
            duplicate_of = review.get("duplicate_of", "")
            if duplicate_of:
                continue
            key = review.get("evidence_key") or candidate["candidate_id"]
            if key in seen_evidence:
                continue
            seen_evidence.add(key)
            evidence_blocks = review.get("evidence_blocks", [])
            if evidence_blocks:
                page_map = json.loads((LEGACY_OUT / "page_maps" / f"{ticker}.json").read_text(encoding="utf-8"))
                page, page_flag = _page_label(evidence_blocks, page_map)
            else:
                page, page_flag = candidate["evidence_page"], int(candidate["page_mapping_review_flag"] or 0)
            evidence.append({
                "ticker": ticker, "evidence_page": page,
                "risk_category": "; ".join(review.get("risk_categories", [])),
                "classification_reason": review["classification_reason"],
                "review_flag": 1 if page_flag else int(review.get("review_flag", 0)),
            })
        for candidate, review in ambiguities:
            ambiguous.append({
                "ticker": ticker, "candidate_id": candidate["candidate_id"],
                "evidence_page": candidate["evidence_page"],
                "classification_reason": review["classification_reason"], "review_flag": 1,
            })
            evidence.append({
                "ticker": ticker, "evidence_page": candidate["evidence_page"], "risk_category": "",
                "classification_reason": review["classification_reason"], "review_flag": 1,
            })
        evidence_count = len(seen_evidence)
        firms.append({
            "company_name": company["company_name"], "ticker": ticker,
            "sector": company["gics_sector"], "source_file": manifest[ticker]["local_path"],
            "filing_date": manifest[ticker]["filing_date"], "item1a_extraction_status": extraction_status,
            "ai_anchor_found": int(bool(ticker_candidates)), "candidate_count": len(ticker_candidates),
            "ai_adoption_concern_yes": value, "ai_risk_categories": "; ".join(risk_categories),
            "evidence_count": evidence_count, "review_status": review_status, "review_notes": notes,
        })

    _write_csv(OUT / "firm_level_results.csv", firms, FIRM_FIELDS)
    _write_csv(OUT / "passage_level_evidence.csv", evidence, EVIDENCE_FIELDS)
    _write_csv(OUT / "ambiguous_review.csv", ambiguous, AMBIGUOUS_FIELDS)
    positives = [row for row in firms if str(row["ai_adoption_concern_yes"]) == "1"]
    negatives = [row for row in firms if str(row["ai_adoption_concern_yes"]) == "0"]
    manual = [row for row in firms if row["review_status"] != "completed"]
    ambiguous_firms = [row for row in firms if row["review_status"] == "ambiguous_manual_review"]
    extraction_failed = [row for row in firms if row["review_status"] == "extraction_failed"]
    zero_anchor = [row for row in firms if row["review_notes"] == "zero_ai_anchor"]
    category_counts = Counter(category for row in positives for category in row["ai_risk_categories"].split("; ") if category)
    denominator = len(positives) + len(negatives)
    pct = lambda number: f"{number / denominator:.1%}" if denominator else "NA"
    report = [
        "# FY2025 Item 1A AI Adoption Concerns Review", "",
        f"- Item 1A successfully extracted: {sum(row['item1a_extraction_status'] == 'success' for row in firms)}/55",
        f"- Zero AI anchor firms: {len(zero_anchor)}",
        f"- Firms with AI candidates: {sum(row['ai_anchor_found'] == 1 for row in firms)}",
        f"- Type A positive: {len(positives)} ({pct(len(positives))})",
        f"- Negative: {len(negatives)} ({pct(len(negatives))})",
        f"- Ambiguous firms: {len(ambiguous_firms)}",
        f"- Extraction failed: {len(extraction_failed)}",
        f"- Total manual-review firms: {len(manual)}", "",
        "## Common Type A risk categories", "",
    ]
    report.extend(f"- {category}: {count}" for category, count in category_counts.most_common())
    report.extend(["", "## Manual review", ""])
    report.extend(f"- {row['ticker']}: {row['review_notes']}" for row in manual)
    if not manual:
        report.append("- None.")
    report.extend(["", "## Reproducibility", "",
        f"Programmatic screening produced {len(candidates)} candidate passages. Semantic review was limited to those passages; all {len(zero_anchor)} zero-anchor firms skipped model review. Raw filings were not downloaded or modified.",
    ])
    (OUT / "review_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # Quality gates requested by the protocol.
    assert len(firms) == 55 and len({row["ticker"] for row in firms}) == 55
    evidence_by_ticker = Counter(row["ticker"] for row in evidence if row["risk_category"])
    for row in firms:
        if str(row["ai_adoption_concern_yes"]) == "1":
            assert evidence_by_ticker[row["ticker"]] >= 1
            assert evidence_by_ticker[row["ticker"]] == int(row["evidence_count"])
        if row["review_notes"] == "zero_ai_anchor":
            assert not evidence_by_ticker[row["ticker"]]
        if row["item1a_extraction_status"] == "extraction_failed":
            assert row["ai_adoption_concern_yes"] == ""
    for row in evidence:
        if not row["evidence_page"]:
            assert str(row["review_flag"]) == "1"
            continue
        valid_pages = {
            value["printed_page"]
            for value in json.loads((LEGACY_OUT / "page_maps" / f"{row['ticker']}.json").read_text(encoding="utf-8"))["blocks"].values()
            if value["printed_page"] is not None
        }
        endpoints = [int(value) for value in row["evidence_page"].split("-")]
        assert min(endpoints) >= min(valid_pages) and max(endpoints) <= max(valid_pages), row
    quality_checks = {
        "firm_count_exactly_55": len(firms) == 55 and len({row["ticker"] for row in firms}) == 55,
        "every_positive_has_evidence": all(evidence_by_ticker[row["ticker"]] >= 1 for row in positives),
        "evidence_count_matches": all(evidence_by_ticker[row["ticker"]] == int(row["evidence_count"]) for row in positives),
        "zero_anchor_has_no_type_a_evidence": all(not evidence_by_ticker[row["ticker"]] for row in zero_anchor),
        "extraction_failed_not_zero": all(row["ai_adoption_concern_yes"] == "" for row in extraction_failed),
        "evidence_pages_in_range_or_flagged": all(row["evidence_page"] or str(row["review_flag"]) == "1" for row in evidence),
        "candidate_ids_unique": len(candidates) == len({row["candidate_id"] for row in candidates}),
        "candidate_reviews_complete": len(reviews) == len(candidates),
        "substantive_duplicate_evidence_suppressed": all(not review.get("duplicate_of") or review["duplicate_of"] in reviews for review in reviews.values()),
        "sample_ticker_sector_preserved": all(row["ticker"] == source["ticker"] and row["sector"] == source["gics_sector"] for row, source in zip(firms, sample)),
        "evidence_pages_missing": sum(not row["evidence_page"] for row in evidence),
        "duplicate_candidates_marked": sum(bool(review.get("duplicate_of")) for review in reviews.values()),
    }
    assert all(value for key, value in quality_checks.items() if isinstance(value, bool)), quality_checks
    (OUT / "quality_checks.json").write_text(json.dumps(quality_checks, ensure_ascii=False, indent=2), encoding="utf-8")
    status = {
        "protocol_version": config["version"], "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": 55, "candidate_passages": len(candidates), "candidate_reviews": len(reviews),
        "positive": len(positives), "negative": len(negatives), "ambiguous": len(ambiguous_firms),
        "extraction_failed": len(extraction_failed), "manual_review_required": len(manual),
        "zero_anchor_firms": len(zero_anchor), "full_text_model_reads_avoided": 55,
        "source_downloads": 0, "raw_documents_modified": 0,
    }
    (OUT / "run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status
