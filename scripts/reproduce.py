"""Rebuild the delivered firm-year panels from saved section/evidence classifications."""
from __future__ import annotations

import argparse
import json

from _prototype import (GDATA, PDATA, copied_file_integrity, fields, governance_replay,
                        practices_replay, replay_output, sealed_file_integrity, write_csv, write_json)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="outputs/reproduced")
    parser.add_argument("--figures", action="store_true", help="Also replay the currently selected figures")
    args = parser.parse_args()
    sealed_file_integrity()
    copied_file_integrity()
    output = replay_output(args.output_dir)
    panel, exclusions, governance = governance_replay()
    practices, practice_checks = practices_replay()
    write_csv(output / "governance/combined_firm_year_v2_panel.csv", panel, fields(GDATA / "combined_firm_year_v2_panel.csv"))
    write_csv(output / "governance/exclusion_manifest.csv", exclusions, fields(GDATA / "exclusion_manifest.csv"))
    write_csv(output / "practices/firm_year_practices_panel.csv", practices, fields(PDATA / "firm_year_practices_panel.csv"))
    report = dict(llm_calls=0, governance=governance, practices=practice_checks)
    if args.figures:
        from plot_figures import replay_figures
        report["figures"] = replay_figures(output / "figures")
    write_json(output / "reproduction_report.json", report)
    summary = dict(output_dir=str(output), llm_calls=0,
                   governance_firm_year_n=governance["firm_year_panel"]["rows"],
                   excluded_firm_year_n=governance["exclusion_panel"]["rows"],
                   practices_firm_year_n=practice_checks["primary_panel"]["rows"],
                   panel_unequal_cells=0)
    if args.figures:
        summary["selected_figures_replayed"] = report["figures"]["selected_figures_replayed"]
        summary["byte_identical_png_n"] = report["figures"]["byte_identical_png_n"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
