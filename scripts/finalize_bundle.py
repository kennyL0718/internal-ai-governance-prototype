"""Create the source manifest and seal an assembled, verified research artifact."""
from __future__ import annotations

import json
import platform
import re
from pathlib import Path

from _prototype import ROOT, copied_file_integrity, fields, read_csv, read_json, sha, write_csv, write_json


def included(path):
    parts = path.relative_to(ROOT).parts
    return not any(part in {".git", ".venv", "__pycache__", "tmp"} for part in parts) and not (len(parts) > 1 and parts[:2] == ("outputs", "reproduced"))


def main():
    source_manifest = ROOT / "docs/source_manifest.csv"
    delivery = ROOT / "docs/delivery_manifest.json"
    if source_manifest.exists() or delivery.exists():
        raise FileExistsError("Refusing to overwrite an existing sealed artifact")
    copied_file_integrity()
    checks = read_json(ROOT / "outputs/validation/prototype_validation.json")
    plots = read_json(ROOT / "outputs/validation/figure_reproduction.json")
    if not checks["passed"] or plots["selected_figures_replayed"] != 10 or plots["byte_identical_png_n"] != 10:
        raise ValueError("Required completed verification evidence is missing")
    records = read_json(ROOT / "outputs/validation/assembly_records.json")
    by_path = {row["prototype_path"]: row for row in records}
    basis = "New artifact documentation, offline adapter, catalogue or assembly validation; source selection is recorded in the audited copy ledger"
    result = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not included(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in by_path:
            result.append(by_path[relative])
            continue
        if relative.startswith("scripts/"):
            purpose = "New portable offline/assembly entry point; original measurement functions remain unchanged"
            operation = "new execution or assembly adapter"
        elif relative.startswith("docs/") or path.name == "README.md":
            purpose = "Researcher-facing artifact documentation or catalogue compiled from audited source files"
            operation = "new documentation or catalogue"
        elif relative.startswith("outputs/validation/"):
            purpose = "New read-only assembly audit or deterministic verification evidence"
            operation = "new assembly validation"
        else:
            purpose = "Artifact environment or packaging metadata"
            operation = "new packaging metadata"
        result.append(dict(prototype_path=relative, original_project_path="[]", original_relative_path="[]",
                           file_type=path.suffix.lstrip(".") or "text", purpose=purpose, classification_version="prototype-assembly-20261029",
                           run_id="", run_identity="prototype-assembly-20261029", selection_basis=basis, operation=operation,
                           transformation="New file; no byte-identical original counterpart. Audit-selected sources are linked by docs/version_audit.md and assembly_records.json.",
                           source_sha256="[]", prototype_sha256=sha(path), bytes=path.stat().st_size,
                           rows=len(read_csv(path)) if path.suffix == ".csv" else ""))
    # These two provenance indexes intentionally omit their own cyclic digests.
    for relative in ["docs/source_manifest.csv", "docs/delivery_manifest.json"]:
        result.append(dict(prototype_path=relative, original_project_path="[]", original_relative_path="[]",
                           file_type=Path(relative).suffix.lstrip("."), purpose="Final provenance index",
                           classification_version="prototype-assembly-20261029", run_id="", run_identity="prototype-assembly-20261029",
                           selection_basis="Indexes the final verified artifact", operation="new provenance index",
                           transformation="Digest omitted here to avoid cyclic index references; delivery_manifest hashes source_manifest and all other included files, excluding itself.",
                           source_sha256="[]", prototype_sha256="", bytes="", rows=""))
    write_csv(source_manifest, result)
    checked_links = 0
    for doc in [ROOT / "README.md"] + list((ROOT / "docs").glob("*.md")):
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            target = target.strip("<>").split("#")[0]
            if not target or "://" in target:
                continue
            checked_links += 1
            if not (doc.parent / target).exists():
                raise ValueError(f"Broken artifact-document link: {doc.name}: {target}")
    files = {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(ROOT.rglob("*")) if path.is_file() and included(path) and path != delivery}
    manifest = dict(artifact="AI Governance Research Prototype", prepared_date="2026-10-29", timezone="Asia/Macau",
                    scope="Existing Governance v2 and frozen P01-P12 Practice measurement only",
                    status="assembled; deterministic replay verified; human semantic validation pending",
                    llm_calls_during_assembly=0, source_project_changes=0,
                    governance=dict(version="implemented-internal-ai-governance-v2.0", recorded_run_id=None,
                                    bundle_identity="full_universe_implemented_internal_ai_governance_v2", started_at_utc="2026-10-13T08:45:17.873118+00:00",
                                    classified_firm_year_n=8500, excluded_firm_year_n=500, positive_n=303, negative_n=8197),
                    practices=dict(run_id="implemented-ai-governance-content-v1-20261018", firm_year_n=303, evidence_n=403,
                                   practice_category_n=12, assignment_n=467, quote_n=606),
                    selected_figures_n=10, selected_pngs_reproduced_byte_identically_n=10,
                    final_document_links_checked=checked_links, final_broken_document_links=[],
                    source_manifest_records=len(result), files=files, files_hashed=len(files),
                    included_bytes_excluding_this_manifest=sum((ROOT / p).stat().st_size for p in files),
                    excluded_generated_paths=["outputs/reproduced/", "tmp/", "__pycache__/", ".venv/"],
                    runtime=dict(python=platform.python_version(), system=platform.system()))
    write_json(delivery, manifest)
    print(json.dumps({k:manifest[k] for k in ["source_manifest_records", "files_hashed", "included_bytes_excluding_this_manifest", "llm_calls_during_assembly"]}, indent=2))


if __name__ == "__main__":
    main()
