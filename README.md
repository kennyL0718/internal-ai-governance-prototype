# AI Governance Research Prototype

Research artifact / proof of concept for an Organization Science Stage 1 submission. Prepared 29 October 2026 from completed project outputs; four proposal presentation panels updated 30 October 2026.

## Research overview

This artifact demonstrates an AI-enabled measurement pipeline for **disclosed evidence of implemented internal AI governance** in US public-company Form 10-K filings. It preserves the completed binary Governance v2 measurement and the frozen, inductively developed P01–P12 governance-practice coding. Original classifications, source identifiers, uncertainty states, prompts and execution records remain traceable.

The results are automated disclosure classifications. Independent human semantic validation remains pending. The artifact does not measure governance effectiveness or establish actual implementation dates.

## Data

The frame contains 1,500 companies from saved S&P 500 / MidCap 400 / SmallCap 600 constituent snapshots, observed over FY2020–FY2025: 9,000 potential firm-years. Item 1A and Item 7 are classified separately; the final analysis unit is CIK × fiscal year.

| Dataset | Complete coverage retained | Main file |
| --- | ---: | --- |
| Final Governance v2 panel | 8,500 firm-years; 1,484 companies | [Governance panel](data/full_sample/governance/combined_firm_year_v2_panel.csv) |
| Double-unavailable exclusions | 500 firm-years, with blank binary labels | [Exclusion manifest](data/full_sample/governance/exclusion_manifest.csv) |
| Section exports | 9,000 records per section; 16,222 classified sections in total | `data/full_sample/governance/item*_v2_classification_results.csv` |
| Final Practices view | All 303 Governance-Positive firm-years; 184 companies | [Practices panel](data/full_sample/practices/firm_year_practices_panel.csv) |
| Practice evidence | All 403 evidence units; 606 supporting practice-label quotes | [Evidence](data/full_sample/practices/evidence_level_practices.csv), [quotes](data/full_sample/practices/practice_quotes.csv) |

Governance has 303 Positive and 8,197 Negative firm-years. Its delivered **observed-section OR** estimator includes 778 single-section observations: 17 Positive and 761 Negative. The `source_status` and section availability fields preserve this distinction. The frozen guideline also describes a stricter two-section negative rule; [methodology](docs/methodology.md) explains the documented estimator used by this delivery.

Practices contain 467 distinct firm-year–practice assignments. Of the 303 Positive firm-years, 281 have at least one assigned practice; 22 have no observed practice assignment. All 303 rows, including uncertainty and review flags, are retained. Governance-Negative and excluded firm-years were outside the practice-coding population.

## Measurement pipeline

1. Read saved, quality-screened complete Item 1A / Item 7 text and its source manifest. Binary v2 uses full section text without keyword screening.
2. Apply the saved v2 standard and complete prompt. Validate the response schema, evidence locations and exception states separately for each section.
3. Aggregate section labels using the original deterministic observed-section OR function. Preserve unavailable, unresolved and accession-conflict states.
4. For Governance-Positive observations, read the 403 existing evidence units and bounded same-chapter context blocks. Apply the frozen inductive codebook; union practice labels across evidence and sections within CIK × fiscal year.

The native practice workflow jointly coded practices, motivations and visions. Its original codebook, schema and native source outputs are retained as dependencies of exact P01–P12 reproduction. The primary practice views expose practice fields only. Separate Pro-AI Orientation, Governance Purpose and other research modules are excluded. A historical plotting file bearing “purpose” in its name supplies shared style functions only.

## Repository structure

```text
prototype/
├── README.md, requirements.txt
├── config/                 Frozen guidelines, full prompts, codebook and LLM snapshots
├── src/
│   ├── governance/         Final historical binary modules and their import dependencies
│   ├── practices/          Frozen native content-coding and aggregation modules
│   └── visualization/      Historical references and copied academic drawing definitions
├── scripts/                Supported offline verification and reproduction adapters
├── data/
│   ├── full_sample/        Complete Governance and Practices results
│   ├── reference/          Fixed size/GICS mapping and upstream source manifests
│   └── sample/             Five native section texts and existing outputs
├── outputs/
│   ├── summary_statistics/ Existing figure data and descriptive statistics
│   └── validation/         Run records, provenance and verification evidence
├── figures/                Eleven current views; historical originals and four academic PNG/PDF pairs
└── docs/                   Methodology, dictionary, version audit and file provenance
```

Start with the [version audit](docs/version_audit.md), [data dictionary](docs/data_dictionary.md), [figure guide](docs/figures.md) and [source manifest](docs/source_manifest.csv). The source manifest distinguishes byte-identical copies from explicit row/column views and newly written documentation.

## Existing results

The selected Governance delivery is `implemented-internal-ai-governance-v2.0`, begun 13 October 2026. Its original manifest does not contain a standalone `run_id`; bundle identity, start timestamp and prompt version identify the run. Practices use `implemented-ai-governance-content-v1-20261018`, with the frozen codebook SHA-256 recorded in the native run manifest.

| Fiscal year | Eligible firm-years | Positive | Positive rate |
| --- | ---: | ---: | ---: |
| 2020 | 1,337 | 2 | 0.15% |
| 2021 | 1,394 | 2 | 0.14% |
| 2022 | 1,409 | 3 | 0.21% |
| 2023 | 1,441 | 35 | 2.43% |
| 2024 | 1,458 | 93 | 6.38% |
| 2025 | 1,461 | 168 | 11.50% |

The figure set covers annual Governance Positive rates, Positive-sample size and GICS composition, Size × Industry rates and 2023–2025 changes, practice distribution, annual practice prevalence and practice-assignment composition. It also includes the pooled size comparison with Financials and Information Technology excluded. Each figure's numerator, denominator, source version and original path are recorded in [figure_registry.csv](docs/figure_registry.csv).

The current guide selects the four academic proposal panels from `figures/proposal_academic_v1_20261030/`. The Practice composition panel contains three pies for FY2023–FY2025, with 54, 135 and 262 assignments; their 451 total is distinct from the full-period 467 assignments. Titles and methodological paragraphs are external to these images in [proposal_figure_notes.md](docs/proposal_figure_notes.md). All ten original exploratory images remain at their previous paths. Classification results, categories and counting rules are unchanged.

## Reproducibility

Use Python 3.12; the verification environment used Python 3.12.14 and the exact package versions in `requirements.txt`. Run from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B scripts\verify.py
.\.venv\Scripts\python.exe -B scripts\reproduce.py --figures
```

The supported entry points work from the bundled files and block network calls and credential loading. `verify.py` reads the artifact and prints its checks. `reproduce.py` rebuilds the two firm-year panels and the exclusion panel; `--figures` replays the eleven currently selected plots. Reproduced files go under `outputs/reproduced/`, leaving sealed results unchanged. A separate figure replay is available through `python -B scripts/plot_figures.py`.

An optional original-source comparison is `python -B scripts/verify.py --source-project ../ai-restrictions-concerns`. The original project is unnecessary for normal offline replay. See [reproducibility.md](docs/reproducibility.md) for validation evidence and the limits of historical entry points.

## Current limitations

- Human semantic accuracy, intercoder reliability and construct validity have not been established by these integrity checks. The inherited review queue contains 134 pending evidence records; 34 evidence units are uncodable and 77 carry a model review flag.
- Size and GICS metadata use a fixed snapshot retrieved on 19 September 2026, applied retrospectively to all years. Historical annual membership and market capitalization are not supplied.
- Complete upstream 10-K acquisition, extraction inputs and bulky API caches remain in the original project. Five full source sections and all practice context blocks are bundled. Fresh provider inference was not run, and exact future provider output is not established.
- This assembly preserves historical `temperature=0` requests with thinking and reasoning effort unspecified. It does not retrofit the shared client's later 25 October configuration.

All existing project files were read or copied only. No DeepSeek request, new classification, literature review or empirical analysis was performed during assembly.
