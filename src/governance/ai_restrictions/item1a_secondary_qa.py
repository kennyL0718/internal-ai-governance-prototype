"""Offline, evidence-bearing secondary QA for retained full-universe Item 1A.

The original extraction is only used to reproduce its saved text. Section
selection here uses a table-of-contents successor, local prose, and heading
context. It does not call the original pair selector or mutate prior files.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .item1a_review import blocks

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/full_universe_item1a"
OUT = BASE / "secondary_qa"
MANIFEST = ROOT / "data/interim/documents/full_universe_item1a_manifest.csv"
START = re.compile(r"^(?:item\s*1\s*a\b[.\s:|–—-]*(?:risk\s*factors\.?\s*)?|risk\s*factors\.?)$", re.I)
END_ITEM = re.compile(r"^item\s*(?:1\s*[.(]?\s*[bc]\)?|2)(?=\W|$)", re.I)
GENERIC_END = {"unresolved staff comments", "cybersecurity", "properties"}
MAJOR_END = re.compile(r"^(?:management[’']?s discussion and analysis|quantitative and qualitative disclosures about market risk|human capital resources and management)\b", re.I)
EXTERNAL = re.compile(r"(?:risk factors?.{0,90}(?:incorporat\w* by reference|set forth in|contained in).{0,100}(?:proxy|exhibit|other document)|(?:incorporat\w* by reference|set forth in).{0,100}(?:risk factors?).{0,100}(?:proxy|exhibit|other document)|information required by this item.{0,220}risk factors.{0,120}incorporat\w*.{0,25}reference)", re.I | re.S)
REFERENCE_DISCLOSURE = re.compile(r"(?:incorporat\w* (?:herein |into this report )?by reference|(?:see|found in|set forth in).{0,160}(?:risk factors|annual report|item 7))", re.I | re.S)
FIELDS = ["ticker", "cik", "fiscal_year", "accession_number", "extraction_status", "extraction_method",
          "original_review_reasons", "secondary_status", "extraction_class", "start_result", "end_result", "content_result",
          "source_verified", "text_reproducible", "repair_attempted", "repair_path", "repair_sha256",
          "source_path", "source_sha256", "item1a_path", "item1a_sha256", "start_block", "end_block_exclusive",
          "start_xpath", "end_xpath", "evidence", "priority"]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").casefold().split())


def substantive(value: str) -> bool:
    value = value.strip()
    return len(value) >= 100 and len(value.split()) >= 15 and sum(c.isalpha() for c in value) >= 65


def start_candidate(value: str) -> bool:
    value = norm(value)
    value = re.sub(r"^part\s*i\.?\s*", "", value, flags=re.I)
    value = re.sub(r"^item\s*1\s*[.(]\s*a\)?", "Item 1A", value, flags=re.I)
    value = re.sub(r"^item\s*i\s*a\b", "Item 1A", value, flags=re.I)
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value) if re.search(r"risk\s*factors", value, re.I) else value
    value = value.rstrip(":").strip()
    return bool(START.fullmatch(value))


def numbered_start(value: str) -> bool:
    """Recognize a heading, never a reference embedded in prose."""
    value = norm(value)
    value = re.sub(r"^part\s*i\.?\s*", "", value)
    value = re.sub(r"^item\s*1\s*[.(]\s*a\)?", "item 1a", value)
    return bool(re.fullmatch(r"item\s*1\s*a\b[.\s:|–—-]*(?:risk\s*factors\.?\s*)?", value, re.I))


def toc_line(data: list[dict], index: int) -> bool:
    toc_markers = [j for j in range(max(0, index - 40), index + 1)
                   if norm(data[j]['text']) in {'table of contents', 'contents'}]
    if toc_markers:
        marker = toc_markers[-1]
        if all(len(data[j]['text']) < 150 for j in range(marker, index + 1)):
            following_navigation = data[marker:min(len(data), marker + 35)]
            first_body = next((j for j, x in enumerate(following_navigation)
                               if len(x['text']) >= 150), len(following_navigation))
            following_navigation = following_navigation[:first_body]
            if sum(bool(re.match(r"^(?:item\s*)?(?:1\s*[abc]|1\s*\([abc]\)|2|3)\b",
                                 norm(x['text']))) for x in following_navigation) >= 3:
                return True
    following = data[index + 1:min(len(data), index + 21)]
    immediate = following[:3]
    numeric = sum(bool(re.fullmatch(r"[\d\s,–—-]{1,22}|n/?a", x["text"], re.I)) for x in following)
    if (any(re.fullmatch(r"[\d\s,–—-]{1,22}|n/?a", x["text"], re.I) for x in immediate)
            and numeric >= 4):
        return True
    left = max(0, index - 10)
    vicinity = data[left:min(len(data), index + 21)]
    first_prose = next((j for j, x in enumerate(vicinity) if len(x['text']) >= 150), None)
    if first_prose is not None:
        if left + first_prose <= index:
            return False
        vicinity = vicinity[:first_prose]
    compact = sum(len(x['text']) < 85 for x in vicinity)
    headings = sum(bool(re.match(r"^(?:item\s*)?(?:1\s*[abc]|1\s*\([abc]\)|2|3)\b", norm(x['text'])))
                   for x in vicinity)
    table_or_links = sum(any(tag in x.get('xpath', '').lower() for tag in ('/table', '/td', '/a['))
                         for x in vicinity)
    return (headings >= 3 and compact >= max(7, len(vicinity) * 3 // 4)
            and (numeric >= 2 or table_or_links >= 3 or compact >= len(vicinity) - 2))


def toc_successors(data: list[dict]) -> set[str]:
    """Collect following TOC labels, allowing a printed page number between labels."""
    result = set()
    limit = min(len(data), 1200)
    for i in range(limit):
        if not start_candidate(data[i]["text"]) or not toc_line(data, i):
            continue
        following = data[i + 1:i + 8]
        for x in following:
            value = norm(x["text"])
            if "risk factors" in value and not END_ITEM.match(value):
                continue
            if value in GENERIC_END or END_ITEM.match(value) or (3 <= len(value) <= 75 and
                value != "risk factors" and not re.fullmatch(r"[\d\s,–—-]+", value)):
                result.add(value)
                break
    return result


def heading_name(data: list[dict], index: int) -> str:
    value = norm(data[index]["text"])
    value = re.sub(r"^anchor\s*", "", value)
    value = re.sub(r"^part\s*i\.?\s*", "", value)
    if END_ITEM.match(value):
        return value
    if value in GENERIC_END:
        return value
    if re.fullmatch(r"1\s*[bc]\.?", value) and index + 1 < len(data):
        return norm(data[index + 1]["text"])
    return value


def local_prose(data: list[dict], start: int, stop: int) -> tuple[int, int]:
    # Count actual paragraph-like blocks rather than heading or navigation words.
    body = [x["text"] for x in data[start + 1:min(stop, start + 100)] if substantive(x["text"])]
    return len(body), sum(len(x) for x in body)


def locate(data: list[dict]) -> dict:
    """Score every plausible heading with TOC, prose and successor evidence."""
    successors = toc_successors(data)
    starts = [i for i, x in enumerate(data) if start_candidate(x["text"])]
    numbered = [i for i in starts if numbered_start(data[i]["text"])]
    candidates = []
    for i in starts:
        toc = toc_line(data, i)
        is_numbered = i in numbered
        # A bare Risk Factors running header is not a new section when a
        # numbered Item 1A heading is available outside the TOC.
        end = None
        for j in range(i + 1, len(data)):
            value = heading_name(data, j)
            if len(value) > 120:
                continue
            if END_ITEM.match(value) and not toc_line(data, j):
                end = j
                break
        body = " ".join(x["text"] for x in data[i + 1:end if end is not None else min(len(data), i + 30)])
        external = bool(REFERENCE_DISCLOSURE.search(body[:2500]))
        prose_count, prose_chars = local_prose(data, i, end if end is not None else len(data))
        short_reference = external and len(body) < 2500
        numbered_nearby = any(i < j < min(i + 4, len(data)) for j in numbered)
        score = (10 if is_numbered else 1) + (6 if end is not None else -12)
        score += (5 if prose_count and prose_chars >= 500 else 4 if short_reference else -8)
        score += 2 if "risk factors" in norm(data[i]["text"]) else 0
        score -= 40 if toc else 0
        score -= 8 if not is_numbered and numbered_nearby else 0
        score -= 6 if not is_numbered and any(j < i and not toc_line(data, j) for j in numbered) else 0
        candidates.append({"block": i, "heading": data[i]["text"], "score": score,
                           "toc": toc, "numbered": is_numbered, "end": end,
                           "prose_chars": prose_chars, "external": external,
                           "short_reference": short_reference})
    ranked = sorted(candidates, key=lambda c: (-c["score"], c["block"]))
    good = [c for c in ranked if not c["toc"] and c["end"] is not None and
            (c["prose_chars"] >= 500 or c["short_reference"] or
             (c["numbered"] and c["prose_chars"] >= 100 and c["end"] - c["block"] <= 6))
            and c["score"] >= 10]
    winner = good[0] if good else None
    if winner is None:
        combined = any(re.match(r"^item\s*1\b", norm(x["text"])) and
                       "risk factors" in norm(x["text"]) and not start_candidate(x["text"])
                       for x in data)
        status = "boundary_unresolved" if starts else "possibly_combined_section" if combined else "no_independent_item1a"
        return {"start": None, "end": None, "successors": sorted(successors),
                "candidates": ranked, "reason": status, "extraction_status": status}
    start, end = winner["block"], winner["end"]
    section = section_text(data, start, end)
    status = ("incorporation_external_reference" if winner["short_reference"] else
              "independent_short_item1a" if winner["prose_chars"] < 500 else "independent_item1a")
    if winner["score"] - (good[1]["score"] if len(good) > 1 else -999) < 3:
        status = "boundary_unresolved"
    return {"start": start, "end": end, "end_title": data[end]["text"],
            "end_basis": "numbered_successor", "successors": sorted(successors),
            "body_candidates": len(good), "candidates": ranked,
            "chosen_candidate": winner, "extraction_status": status,
            "reason": "" if status != "boundary_unresolved" else "competing_body_headings"}


def section_text(data: list[dict], start: int, end: int) -> str:
    return "\n\n".join(x["text"] for x in data[start:end]) + "\n"


def evidence_anchors(saved: str, selected: str, data: list[dict], start: int, end: int) -> dict:
    """Check separated source paragraphs, not just matching a header string."""
    source_paragraphs = [x["text"] for x in data[start:end] if substantive(x["text"])]
    if len(source_paragraphs) < 2:
        return {"pass": False, "found": 0, "count": len(source_paragraphs)}
    locations = sorted({0, len(source_paragraphs) // 2, len(source_paragraphs) - 1})
    found = sum(norm(source_paragraphs[i][:120]) in norm(saved) for i in locations)
    return {"pass": found == len(locations) and norm(selected[:200]) in norm(saved[:500]),
            "found": found, "count": len(locations),
            "first": source_paragraphs[0][:120], "last": source_paragraphs[-1][:120]}


def repeated_large(text: str) -> bool:
    paragraphs = [norm(p) for p in text.split("\n\n") if len(p.strip()) > 500]
    return any(n > 1 for n in Counter(paragraphs).values())


def validate_text(text: str, data: list[dict], location: dict) -> dict:
    start, end = location.get("start"), location.get("end")
    if start is None or end is None:
        return {"passed": False, "start": "unresolved" if start is None else "located",
                "end": "unresolved", "content": "unresolved", "reason": location.get("reason", "")}
    expected = section_text(data, start, end)
    reproducible = text == expected
    anchor = evidence_anchors(text, expected, data, start, end)
    body_blocks = [x["text"] for x in data[start:end] if substantive(x["text"])]
    body_chars = sum(len(x) for x in body_blocks)
    external = location.get("extraction_status") == "incorporation_external_reference"
    repeated = repeated_large(text)
    next_leak = bool(re.search(r"(?:^|\n\n)(?:item\s*1\s*[bc]|item\s*2)\b", text, re.I))
    # Exact equality establishes coverage against the independently selected
    # source interval. Heading and dispersed paragraph anchors support it.
    reference_complete = external and reproducible and start_candidate(data[start]["text"]) and end > start + 1
    short_complete = (location.get("extraction_status") == "independent_short_item1a"
                      and reproducible and body_chars >= 100 and end - start <= 6)
    passed = (reproducible and (reference_complete or short_complete or (anchor["pass"] and body_chars >= 500))
              and not repeated and not next_leak and location.get("extraction_status") != "boundary_unresolved")
    return {"passed": passed, "start": "verified" if anchor["pass"] or reference_complete or short_complete else "mismatch",
            "end": "verified" if reproducible else "mismatch", "content": ("external_reference" if external else
            "repeated_large_block" if repeated else "next_section_leak" if next_leak else
            "verified" if short_complete or anchor["pass"] and body_chars >= 500 else "unresolved"),
            "reason": "" if passed else ";".join(k for k, v in {
                "section_text_mismatch": not reproducible, "paragraph_anchors_missing": not anchor["pass"],
                "external_reference": external, "repeated_large_block": repeated,
                "next_section_leak": next_leak, "insufficient_body": body_chars < 500}.items() if v),
            "expected": expected, "anchor": anchor, "body_chars": body_chars,
            "reproducible": reproducible}


def process(row: dict, *, repair: bool = True, repair_root: Path = OUT) -> tuple[dict, dict | None]:
    base = {field: "" for field in FIELDS}
    base.update(ticker=row["ticker"], cik=row["cik"], fiscal_year=row["fiscal_year"],
                accession_number=row["accession_number"], extraction_status=row["extraction_status"],
                extraction_method=row["extraction_method"], original_review_reasons=row["review_reason"],
                source_path=row["local_path"], source_sha256=row["sha256"],
                item1a_path=row["item1a_path"], item1a_sha256=row["item1a_sha256"],
                secondary_status="unresolved", source_verified="0", repair_attempted="0")
    src, txt = ROOT / row["local_path"], ROOT / row["item1a_path"]
    if not src.is_file() or not txt.is_file():
        base["evidence"] = "retained original or saved text absent"
        return base, None
    if sha(src) != row["sha256"] or sha(txt) != row["item1a_sha256"]:
        base["evidence"] = "source or text hash differs from manifest"
        return base, None
    base["source_verified"] = "1"
    text = txt.read_text(encoding="utf-8")
    data = blocks(src)
    loc = locate(data)
    check = validate_text(text, data, loc)
    s, e = loc.get("start"), loc.get("end")
    base.update(extraction_class=loc.get("extraction_status", "boundary_unresolved"),
                start_result=check["start"], end_result=check["end"], content_result=check["content"],
                text_reproducible="1" if check.get("reproducible") else "0",
                start_block="" if s is None else s, end_block_exclusive="" if e is None else e,
                start_xpath="" if s is None else data[s]["xpath"],
                end_xpath="" if e is None else data[e]["xpath"],
                evidence=json.dumps({"start_heading": data[s]["text"] if s is not None else "",
                    "end_heading": loc.get("end_title", ""), "end_basis": loc.get("end_basis", ""),
                    "toc_successors": loc.get("successors", []), "body_candidates": loc.get("body_candidates", 0),
                    "candidate_positions": loc.get("candidates", []),
                    "chosen_candidate": loc.get("chosen_candidate"),
                    "extraction_class": loc.get("extraction_status", "boundary_unresolved"),
                    "paragraph_anchors": check.get("anchor", {}), "body_chars": check.get("body_chars", 0),
                    "reason": check["reason"]}, ensure_ascii=False))
    reasons = set(filter(None, row["review_reason"].split(";")))
    process_issue = bool(reasons & {"amendment_or_batch_audit_unresolved"}) or bool(row.get("amendment_accessions"))
    if check["content"] == "external_reference" and check["passed"] and not process_issue:
        base["secondary_status"] = "auto_verified"
    elif check["content"] == "external_reference":
        base["secondary_status"] = "external_source_required"
    elif check["passed"] and not process_issue:
        base["secondary_status"] = "auto_verified"
    elif check["passed"] and process_issue:
        base["secondary_status"] = "manual_review_required"
        base["evidence"] += "; filing-selection or amendment issue remains"
    elif s is None or e is None:
        base["secondary_status"] = "unresolved"
    elif check["content"] in ("repeated_large_block", "next_section_leak") and check["reproducible"]:
        base["secondary_status"] = "manual_review_required"
    else:
        base["secondary_status"] = "confirmed_error" if (not check["reproducible"] and
            check["anchor"]["count"] >= 2 and check["body_chars"] >= 500) else "manual_review_required"
    repair_record = None
    if repair and base["secondary_status"] == "confirmed_error" and s is not None and e is not None:
        base["repair_attempted"] = "1"
        candidate = section_text(data, s, e)
        repaired_check = validate_text(candidate, data, loc)
        repair_record = {"ticker": row["ticker"], "fiscal_year": row["fiscal_year"],
                         "accession_number": row["accession_number"], "original_path": row["item1a_path"],
                         "original_sha256": row["item1a_sha256"], "original_characters": len(text),
                         "source_path": row["local_path"], "source_sha256": row["sha256"],
                         "start_block": s, "end_block_exclusive": e, "repair_reason": check["reason"],
                         "verification": ("passed" if repaired_check["passed"] and not process_issue else
                                          "text_passed_selection_open" if repaired_check["passed"] else repaired_check["reason"])}
        stageable = (repaired_check["start"] == "verified" and repaired_check["end"] == "verified"
                     and repaired_check["content"] != "next_section_leak")
        if stageable:
            dest = repair_root / "repaired_text" / f"FY{row['fiscal_year']}" / f"{row['ticker']}_FY{row['fiscal_year']}_Item1A.txt"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and dest.read_text(encoding="utf-8") != candidate:
                raise ValueError(f"Existing repair differs: {dest}")
            if not dest.exists():
                with dest.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(candidate)
            base.update(secondary_status="repaired_verified" if repaired_check["passed"] and not process_issue
                        else "manual_review_required", repair_path=dest.relative_to(ROOT).as_posix(),
                        repair_sha256=sha(dest), start_result="verified_after_repair",
                        end_result="verified_after_repair", content_result="verified_after_repair" if repaired_check["passed"]
                        else repaired_check["content"])
            repair_record.update(repair_path=base["repair_path"], repair_sha256=base["repair_sha256"],
                                 repaired_characters=len(candidate))
        else:
            repair_record.update(repair_path="", repair_sha256="", repaired_characters="")
    return base, repair_record


def priority(row: dict) -> int:
    state = row["secondary_status"]
    if state == "confirmed_error": return 1
    if row["content_result"] in {"next_section_leak", "external_reference"}: return 2
    if state == "manual_review_required": return 3
    return 4


def run(*, sample: set[tuple[str, str]] | None = None, repair: bool = True,
        dest: Path = OUT) -> dict:
    dest = dest.resolve()
    manifest = read_csv(MANIFEST)
    rows = [r for r in manifest if r["extraction_status"] == "success" and r["quality_status"] == "review_required"]
    if len(rows) != 3541 or len({(r["ticker"], r["fiscal_year"]) for r in rows}) != 3541:
        raise ValueError(f"Review cohort changed: {len(rows)}")
    if sample is not None:
        rows = [r for r in rows if (r["ticker"], r["fiscal_year"]) in sample]
    result, repairs = [], []
    for index, row in enumerate(rows, 1):
        try:
            outcome, repair_row = process(row, repair=repair, repair_root=dest)
        except Exception as exc:
            outcome = {field: "" for field in FIELDS}
            outcome.update(ticker=row["ticker"], cik=row["cik"], fiscal_year=row["fiscal_year"],
                           accession_number=row["accession_number"], extraction_status=row["extraction_status"],
                           extraction_method=row["extraction_method"], original_review_reasons=row["review_reason"],
                           source_path=row["local_path"], item1a_path=row["item1a_path"],
                           source_sha256=row["sha256"], item1a_sha256=row["item1a_sha256"],
                           secondary_status="unresolved", evidence=f"processor exception: {type(exc).__name__}: {exc}")
            repair_row = None
        outcome["priority"] = priority(outcome)
        result.append(outcome)
        if repair_row: repairs.append(repair_row)
        if index % 250 == 0:
            print(f"secondary QA {index}/{len(rows)}", flush=True)
    dest.mkdir(parents=True, exist_ok=True)
    write_csv(dest / "secondary_qa_results.csv", result, FIELDS)
    remaining = sorted((r for r in result if r["secondary_status"] not in {"auto_verified", "repaired_verified"}),
                       key=lambda r: (r["priority"], r["fiscal_year"], r["ticker"]))
    write_csv(dest / "manual_review_queue.csv", remaining, FIELDS)
    write_csv(dest / "priority_manual_review.csv", remaining[:300], FIELDS)
    write_csv(dest / "validation_evidence.csv", result, FIELDS)
    repair_fields = list(repairs[0]) if repairs else ["ticker", "fiscal_year", "accession_number", "original_path",
        "original_sha256", "original_characters", "source_path", "source_sha256", "start_block", "end_block_exclusive",
        "repair_reason", "verification", "repair_path", "repair_sha256", "repaired_characters"]
    write_csv(dest / "repair_manifest.csv", repairs, repair_fields)
    counts = Counter(r["secondary_status"] for r in result)
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "cohort": len(rows),
               "statuses": dict(counts), "remaining": len(remaining), "repair_attempts": len(repairs)}
    (dest / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary
