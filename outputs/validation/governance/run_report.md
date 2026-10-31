# Full-Universe Implemented Internal AI Governance v2

## A. Executive Summary

Status: complete. Target=9000; Eligible=8500; Excluded=500; Positive=303; Negative=8197; Unresolved=0. Overall Positive Rate: 3.5647%.
Model estimates of disclosed evidence; no human-review decisions or governance quality scores are inferred.

## B. Data Coverage

Item 1A valid text: 8195/9000. Item 7 valid text: 8027/9000.
The final LLM exception queue is empty. Both sections observed=7,722; only Item 1A observed=473; only Item 7 observed=305. Source exceptions: `source_exception_manifest.csv`; double-unavailable observations: `exclusion_manifest.csv`; unresolved LLM cases: `classification_exception_queue.csv`. Reasons distinguish acquisition, extraction, identity, incorporated-reference and input-validation failures.
Item 1A uses original automatic-pass text, independently verified original text, and saved secondary repaired_verified text with matching accession/hash. The latest review-repair comparison overrides older verification; unresolved staged candidates and filing-selection cases remain unavailable. Item 7 uses the latest v2.4 extraction manifest, success plus automatic_pass only.

| FY | Item 1A N | Item 1A Coverage | Item 7 N | Item 7 Coverage | Double Unavailable |
|---|---:|---:|---:|---:|---:|
| 2020 | 1310 | 87.33% | 1242 | 82.80% | 163 |
| 2021 | 1336 | 89.07% | 1313 | 87.53% | 106 |
| 2022 | 1346 | 89.73% | 1333 | 88.87% | 91 |
| 2023 | 1384 | 92.27% | 1367 | 91.13% | 59 |
| 2024 | 1402 | 93.47% | 1394 | 92.93% | 42 |
| 2025 | 1417 | 94.47% | 1378 | 91.87% | 39 |

## C. LLM Configuration

DeepSeek / `deepseek-flash` (intended `DeepSeek-V4.1-Flash`); temperature=0; max_tokens=16384; JSON object response; timeout=120s; 3 transport retries, 2/4/8s backoff; at most 2 validation requests. Concurrency=64.
Settings baseline: `data/interim/classifications/full_universe_item7_implemented_internal_ai_governance/v1/run_manifest.json`, the most recent completed full-universe Item 7 governance workflow (2026-10-10). Same shared DeepSeek client and payload builder; only an optional raw-response capture callback was added.
Prompt `implemented-internal-ai-governance-v2.0`: `system_prompt.txt`, `user_prompt_template.txt`; complete authoritative standard: `classification_standard_snapshot.md`. API attempts=20845; received responses=16639. Tokens={'prompt_tokens': 338355622, 'completion_tokens': 16046104, 'total_tokens': 354401726, 'prompt_cache_hit_tokens': 83251517, 'prompt_cache_miss_tokens': 255104105}. Actual account cost unavailable; verified list-price scenarios are reported below; credentials excluded.
Every attempt is in `request_manifest.jsonl`, referring to exact full message snapshots in `requests/`; raw API responses are in `responses/`, validated results and source quote offsets in `cache/`. Hashes link source bytes, prompts, request payload and response. Resumes use the same source/prompt/configuration digest and skip all completed or review responses.

Published list-price scenarios based on all API-returned usage (including received retries): USD 48.1430 off-peak / 96.2861 peak; CNY 320.9536 / 641.9071. The balance endpoint returned CNY. Account invoice and itemized credit deductions were not retrieved; USD figures are separate published-price scenarios. Sources: [DeepSeek USD pricing](https://api-docs.deepseek.com/quick_start/pricing/) and [CNY pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/), snapshot retrieved 2026-10-13. See `pricing_snapshot.json` and `cost_and_token_summary.json`.

## D. Classification Results

| FY | Target | Eligible | Excluded | Positive | Negative | Unresolved | Positive Rate | 1A Positive | 7 Positive | Both | Only 1A | Only 7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 1500 | 1337 | 163 | 2 | 1335 | 0 | 0.150% | 0 | 2 | 0 | 0 | 2 |
| 2021 | 1500 | 1394 | 106 | 2 | 1392 | 0 | 0.143% | 0 | 2 | 0 | 0 | 2 |
| 2022 | 1500 | 1409 | 91 | 3 | 1406 | 0 | 0.213% | 1 | 2 | 0 | 1 | 2 |
| 2023 | 1500 | 1441 | 59 | 35 | 1406 | 0 | 2.429% | 30 | 6 | 1 | 29 | 5 |
| 2024 | 1500 | 1458 | 42 | 93 | 1365 | 0 | 6.379% | 85 | 8 | 0 | 85 | 8 |
| 2025 | 1500 | 1461 | 39 | 168 | 1293 | 0 | 11.499% | 156 | 14 | 2 | 154 | 12 |

## E. Figures

![Annual positive rate](figures/figure1_annual_positive_rate.png)
![Annual positive count](figures/figure2_annual_positive_count.png)
![Combined figures](figures/combined_annual_trends.png)
All six years are complete. Positive Rate uses annual Eligible N; each plotted count is the final observed-section OR count. PNG 300 dpi and vector PDF.

## F. QA and Limitations

Response recovery: 48 cases were recovered offline without changing the model label, using exact source spans after unique typography/whitespace or recognized paired page-number/TOC alignment. 79 distinct sections received corrective full-text calls (including three source-based semantic QA cases); 23 of them received a second and last corrective round. The authoritative System Prompt, standard, model, temperature and output budget stayed identical; saved user suffixes constrained formatting and requested reinspection under C3/C4. Negative evidence arrays may be empty after a new full-section LLM judgment; failed responses were never converted into Negative. One additional KVUE FY2025 quote was recovered through a separately documented inspection of page number 26, restoring the complete exact source span and keeping its Positive label. Original responses and caches remain in `responses/`, `recovery_originals/`, and `semantic_qa_originals/`. See `offline_response_recovery.csv`, `corrective_recovery_summary.csv`, `semantic_source_review_manifest.csv`, `verified_pagination_recovery.json`, both corrective user-suffix templates and both recovery configuration files.

QA checks passed: True; all eligible binary complete: True. Details: `qa.json`.
The user task section 5.1 explicitly adopts an observed-section estimator: a single available classified Negative plus unavailable text is 0. This is the expressly selected alternative permitted by standard section 5.2; it does not establish a complete two-section negative. `source_status` and coverage flags retain that distinction.
OR returns 1 for qualifying evidence in either section; unresolved classification in the other section is retained in its exception queue. With no positive, pending/review/API/JSON errors block 0. Dual unavailable valid text alone causes exclusion. Conflicting accessions among valid chapters are held for review.
Automated extraction checks cannot establish human boundary correctness. Missing/unverified text can select the eligible sample; current frozen index constituents also create survivorship/selection limits. Negative denotes absent evidence in observed disclosure, not absent real governance.
v2 requires C1-C5 and excludes bare restrictions unless additional implemented institutional evidence exists. v1 labels and G/R subtype fields were neither input nor mapped into v2. A positive quote source match establishes traceability, not semantic correctness; `positive_evidence_audit.csv` retains all positive cases for inspection.
Model material timing/actor/mechanism ambiguity remains an explicit null review state. Annual rates are withheld for unfinished years. No causal or governance-quality inference is made.

The primary run encountered HTTP 402; `interruption_manifest.json` records the interruption. The user confirmed top-up and the run resumed from validated caches. A billing circuit breaker now stops queued submissions on HTTP 402. Historical failed attempts remain in request accounting, with missing usage left unknown. All 16,222 valid sections now have compliant binary results; all 8,500 eligible firm-years are resolved.

Focused offline tests: 42 passed. Independent delivery checks in `delivery_qa.json` reconcile CSV keys, source availability, exclusions, OR rules, annual denominators/rates, original Item 1A bytes and credential exclusion. `positive_evidence_contexts.jsonl` supplies adjacent source context and normalized-text character offsets for every positive quote. `restriction_mention_positive_inspection.csv` contains 24 source-inspected positive sections with restriction/prohibition wording. Each has additional policy, committee, review, monitoring/enforcement, compliance-program or executed technical-risk-control evidence; no bare-restriction-only positive was identified in this inspected set. Inspection notes are machine source QA and are neither human decisions nor a new classification subtype.

Observed trends: Positive N is 2, 2, 3, 35, 93 and 168 from FY2020 to FY2025; Positive Rate is 0.150%, 0.143%, 0.213%, 2.429%, 6.379% and 11.499%. Coverage also increases over this period, so these disclosed-evidence trends do not identify changes in actual governance prevalence or a causal effect.

## Artifact paths

- `outputs/full_universe_implemented_internal_ai_governance_v2/item1a_v2_classification_results.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/item7_v2_classification_results.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/combined_firm_year_v2_panel.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/annual_trend_summary.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/exclusion_manifest.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/positive_evidence_audit.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/classification_exception_queue.csv`
- `outputs/full_universe_implemented_internal_ai_governance_v2/qa.json`
- `outputs/full_universe_implemented_internal_ai_governance_v2/request_manifest.jsonl`
- `outputs/full_universe_implemented_internal_ai_governance_v2/llm_config.json`
- `outputs/full_universe_implemented_internal_ai_governance_v2/run_manifest.json`
