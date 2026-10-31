"""Shared, unchanged implemented-governance v1 schema and cache contract."""
from pathlib import Path
import hashlib
import json
from . import item1a_semantic as prior
from .llm import implemented_governance_prompt as prompt
from .llm.client import chat_json, PROVIDER, MODEL

FIELDS = ["company", "ticker", "fiscal_year", "risk_factor_heading", "classification", "implemented_internal_ai_governance", "governance_evidence_type", "implementation_evidence", "ai_specificity_evidence", "reason", "manual_review", "review_reason"]
TYPES = {"G1", "G2", "G3", "R1", "R2"}


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def key(row: dict) -> tuple[str, str, str]:
    return row["ticker"], str(row["fiscal_year"]), row["candidate_id"]


def norm(value: str) -> str:
    return prior._normal(value)


def validate(result: dict, candidate: dict) -> dict:
    if not isinstance(result, dict) or not set(FIELDS) <= set(result):
        raise ValueError("Missing required governance JSON fields")
    if str(result["ticker"]).upper() != candidate["ticker"] or str(result["fiscal_year"]) != candidate["fiscal_year"]:
        raise ValueError("LLM returned wrong firm-year")
    classification = result["classification"]
    value = result["implemented_internal_ai_governance"]
    evidence_types = result["governance_evidence_type"]
    if classification not in {"positive", "negative", "ambiguous"} or not isinstance(evidence_types, list) or not set(evidence_types) <= TYPES or len(evidence_types) != len(set(evidence_types)):
        raise ValueError("Invalid governance label or evidence types")
    if type(result["manual_review"]) is not bool or not str(result["reason"]).strip():
        raise ValueError("Invalid review flag or missing reason")
    source = norm(candidate["candidate_text"] + " " + candidate.get("surrounding_context", ""))
    for field in ("implementation_evidence", "ai_specificity_evidence"):
        quote = str(result[field]).strip()
        if quote and norm(quote) not in source:
            raise ValueError(f"{field} is not a contiguous quote in saved Item 1A")
    if classification == "positive":
        if type(value) is not int or value != 1 or not evidence_types or not all(str(result[f]).strip() for f in ("implementation_evidence", "ai_specificity_evidence")):
            raise ValueError("Positive lacks label, type, or locatable source evidence")
        if not result["manual_review"] or not str(result["review_reason"]).strip():
            raise ValueError("Preliminary positive must enter manual review")
    elif classification == "negative":
        if type(value) is not int or value != 0 or evidence_types:
            raise ValueError("Negative label is inconsistent")
    else:
        if value is not None or evidence_types or not result["manual_review"] or not str(result["review_reason"]).strip():
            raise ValueError("Ambiguous must remain unresolved with review reason")
    if result["manual_review"] and not str(result["review_reason"]).strip():
        raise ValueError("Review flag lacks reason")
    return result


def cache_path(candidate: dict, system: str, output_dir: Path, *, prompt_version=None, payload=None) -> Path:
    identity = json.dumps([prompt_version or prompt.PROMPT_VERSION, sha(system.encode()), PROVIDER, MODEL, payload if payload is not None else prior._payload(candidate)], ensure_ascii=False).encode()
    return output_dir / "cache" / f"FY{candidate['fiscal_year']}_{candidate['ticker']}_{candidate['candidate_id']}_{sha(identity)[:20]}.json"


def classify(candidate: dict, system: str, config, output_dir: Path, attempt_observer=None, *, prompt_version=None, payload=None, max_tokens=4096) -> dict:
    path = cache_path(candidate, system, output_dir, prompt_version=prompt_version, payload=payload)
    if path.is_file():
        record = json.loads(path.read_text(encoding="utf-8"))
        record["cache_status"] = "hit"
    else:
        kwargs = {'attempt_observer': attempt_observer} if attempt_observer else {}
        result, metadata = chat_json(system, payload if payload is not None else prior._payload(candidate), config=config, max_tokens=max_tokens, **kwargs)
        record = {"result": result, **metadata, "classified_at_utc": prior._now(), "candidate_sha256": sha(candidate["candidate_text"].encode())}
        prior._write_json(path, record)  # paid raw JSON survives a validation failure
    validate(record["result"], candidate)
    return record


def decision(available, expected, items, errors):
    positives = [r for r in items if r['classification'] == 'positive']
    ambiguous = [r for r in items if r['classification'] == 'ambiguous']
    complete = not errors and len(items) == expected
    if not available:
        return '', 'missing_or_unreliable_item1a'
    if positives:
        return '1', 'positive' if complete else 'preliminary_positive'
    if errors or ambiguous or not complete:
        return '', 'unresolved_classification'
    return ('0', 'no_ai_anchor') if expected == 0 else ('0', 'all_candidates_negative')
