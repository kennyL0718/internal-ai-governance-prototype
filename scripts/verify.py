"""Check the saved artifact and replay its deterministic aggregation without API calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _prototype import (ROOT, copied_file_integrity, credential_scan, governance_replay,
                        practices_replay, sample_smoke, sealed_file_integrity, write_json)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-project", type=Path, help="Optional read-only comparison against the original project")
    parser.add_argument("--report", type=Path, help="Write a new report; refuses to replace an existing report")
    args = parser.parse_args()
    source = args.source_project.resolve() if args.source_project else None
    report = {"artifact": "AI Governance Research Prototype", "llm_calls": 0,
              "sealed_files": sealed_file_integrity(), "copied_files": copied_file_integrity(source)}
    _, _, report["governance"] = governance_replay()
    _, report["practices"] = practices_replay()
    report["sample_non_api_smoke"] = sample_smoke()
    report["credentials"] = credential_scan()
    report["passed"] = True
    report["unverified"] = ["Fresh provider inference and bitwise reproducibility of model outputs",
                            "Independent human semantic accuracy",
                            "Full-universe upstream 10-K acquisition and text extraction"]
    if args.report:
        path = args.report if args.report.is_absolute() else ROOT / args.report
        path = path.resolve()
        if not path.is_relative_to(ROOT / "outputs") or path.exists():
            raise ValueError("Report must be a new file within prototype/outputs")
        write_json(path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
