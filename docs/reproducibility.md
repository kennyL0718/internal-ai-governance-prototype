# Reproduction status and supported execution

All commands below run from the prototype root. They use paths resolved from the script location and require no original-project directory for normal replay. The original full-sample model outputs remain unchanged.

## Verified offline functions

`python -B scripts/verify.py` checks sealed/copy hashes, rebuilds the 8,500-row Governance panel and 500-row exclusion panel through the original final `aggregate` function, and compares all 29 fields per row. It also reconstructs the original 303-row native content panel through its original union function and compares all 108 native fields, then checks the 28-field primary Practice view. All 403 native evidence results pass the original structural/category/status/context-quote validator; all 606 Practice quote rows match their stored locations.

Five native section examples cover one Negative, four Positive sections, early-year evidence, a concrete legal/security review, and a firm-year Positive in both chapters. Their source hashes, schema/evidence validation and complete system prompt are checked without inference. Historical request bodies are assembled locally; no response is generated. These examples provide an execution smoke test and are not an accuracy evaluation set.

All five binary request-body hashes match the original section exports. One original saved Practice request also matches the frozen runtime builder and hash exactly. That check resolves the extra trailing instruction in the saved readable Practice template; the exact runtime scaffold is stored separately, leaving the original snapshot unchanged.

`python -B scripts/reproduce.py` writes rebuilt Governance, exclusion and Practice panels under `outputs/reproduced/`. Adding `--figures` replays all eleven currently selected figures. `python -B scripts/plot_figures.py` runs just the figure replay. The report compares PNG bytes and pixels with the selected prototype assets. The initial assembly reproduced its original ten PNGs byte for byte; the 30 October presentation update is recorded separately in `outputs/validation/figure_reproduction_academic_20261030.json`. Exact rendering on another operating system or package version has not been established.

The original ten figures remain unchanged at their historical `figures/` paths. Four academic PNG/PDF pairs are selected through `docs/figure_presentation_updates.json`; the current registry contains seven original views and four academic panels. Replay outputs remain separate. `outputs/validation/figure_reproduction.json` retains the initial assembly comparison, and `prototype_validation.json` retains its deterministic checks. The original-project audit additionally checked all 306 Positive source text hashes and the evidence/quote locations against those full texts; only five full texts are bundled.

Temporary replay outputs and the relocation-test copy were removed after their verification reports were retained. Historical generated paths in those reports describe the check location; running the supported commands recreates replay outputs under `outputs/reproduced/`.

## Why adapters are needed

The historical modules assume their original repository layout and combine measurement with execution/report writers. The supported adapter imports the unmodified copied modules under separate package namespaces, supplies relocated paths and calls their pure validation/aggregation functions. It blocks network connections, transports, inference functions and credential loading.

Historical visualization modules also resolve old paths at import time and contain plots for unrelated projects. The figure adapter compiles explicitly named copied function definitions and binds local data paths and shared style functions. The source definitions and their hashes are recorded in the replay report. The original content renderer is limited to its existing Practice frequency and annual-prevalence blocks; its plotting expressions are preserved. Categories, labels and denominator rules are unchanged. The separately versioned academic views remove embedded titles/notes, and the assignment-composition view uses three annual pies with the requested FY2023–FY2025 restriction. Complete methodological notes and the full-period reconciliation are in [proposal_figure_notes.md](proposal_figure_notes.md).

Unchanged shared plotting reference files can contain unused branches for other disclosure variables. The portable adapter executes only Governance, Practice and shared-style definitions; it does not load separate Orientation or Purpose datasets or classifier modules.

`src/governance/reference_entrypoints/` and `src/practices/reference_entrypoints/` preserve original orchestration for inspection. Their original package/layout assumptions and external data dependencies prevent direct standalone execution from their relocated archival paths. The supported portable commands are the scripts above.

## Environment

The assembly reused the existing project environment: Python 3.12.14, matplotlib 3.11.2, numpy 2.5.3, Pillow 12.3.0 and PyYAML 6.0.3. Exact versions are pinned in `requirements.txt`. A clean environment installation and non-Windows rendering were not performed. Standard-library CSV/JSON operations preserve identifiers as strings; no pandas dependency is needed by the supported scripts.

## External or unverified functions

| Function | Status / prerequisites |
| --- | --- |
| Saved-result checks and deterministic aggregation | Verified from bundled complete classifications |
| Practice schema/context-quote validation | Verified for all 403 evidence results from bundled inputs |
| Sample binary validation and historical request assembly | Verified for five bundled section texts |
| Selected plot replay | Initial ten-figure verification retained; current eleven-figure replay verified separately in the recorded environment |
| Full-universe source TXT hash recheck | Full original files required; the assembly checked all Positive sources, and source existence for all 16,222 valid inputs |
| Upstream acquisition / full extraction | Not rerun; complete upstream corpora, extraction state and original environment required |
| Historical cache-based original `report` stages | Bulky caches and original layout required; portable replay uses saved section/evidence exports instead |
| Fresh binary or Practice inference | Not executed; requires separate authorization, complete inputs, compatible historical configuration and provider access |
| Human semantic validation / accuracy | Pending; no human decisions or reliability statistic created |

The original binary `prepare` stage additionally depends on the upstream secondary-QA table `outputs/full_universe_item1a/secondary_qa/secondary_qa_results.csv`, the repair comparison `data/interim/documents/item1a_review_repair_20260930_v3/comparison.csv`, and the baseline settings manifest `data/interim/classifications/full_universe_item7_implemented_internal_ai_governance/v1/run_manifest.json`, alongside the source manifests and full section texts. The original reporting stages require their cache, request/response, protection and pilot state. Practice `prepare` also reads the original binary evidence-context bundle; portable replay instead includes its already prepared 403 evidence units. These external stages were preserved for inspection and were not executed.

The original request-log hashes and compact complete failure/error event views are bundled. Full requests, responses, cache state and original execution logs remain in the source project. Original historical failure events are preserved separately from zero final classification failures. No secret keys, `.env` files or credentials are required by the supported offline entry points.

## Provenance checks and maintenance

Use `python -B scripts/verify.py --source-project PATH_TO_ORIGINAL_PROJECT` for an optional read-only check of original source hashes. Without this option, the prototype checks only its bundled inputs and sealed files and remains portable.

`scripts/assemble_from_project.py` documents the one-time copy/view assembly and refuses to overwrite existing destinations. `scripts/finalize_bundle.py` creates the source manifest and seals the finished artifact after documentation and validation. These are assembly tools; they are unnecessary for routine reviewer replay. Temporary replay outputs, local environments and caches are excluded from the sealed deliverable inventory.
