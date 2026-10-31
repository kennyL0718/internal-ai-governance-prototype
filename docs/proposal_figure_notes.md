# Proposal Figure Notes

These notes accompany the four academic presentation panels selected in this prototype. The ten original exploratory assets remain at their historical paths. Entries are identified by filenames and directories; captions have no fixed figure numbers. PNG files are 300 dpi, and PDF files are vector exports with embedded fonts.

## implementation/figure1_annual_positive_rate.png

**Suggested caption:** Annual prevalence of disclosed implemented internal AI governance, FY2020–FY2025.

**Files:** [PNG](../figures/proposal_academic_v1_20261030/implementation/figure1_annual_positive_rate.png) · [PDF](../figures/proposal_academic_v1_20261030/implementation/figure1_annual_positive_rate.pdf) · [original exploratory PNG](../figures/governance/annual_positive_rate.png).

**Data and period.** [Governance v2 firm-year panel](../data/full_sample/governance/combined_firm_year_v2_panel.csv) and [annual control table](../outputs/summary_statistics/governance/annual_trend_summary.csv), FY2020–FY2025; version `implemented-internal-ai-governance-v2.0`.

**Measurement and aggregation.** The annual rate is positive firm-years divided by valid binary firm-years. Each CIK × fiscal year is counted once across Item 1A and Item 7. At least one available, successfully classified section is required. A positive section yields a positive firm-year; one observed negative section with the other unavailable remains negative under the original observed-section OR estimator. Double-unavailable observations and missing CIK records remain excluded, with no imputation.

| Fiscal year | Valid firm-years | Positive firm-years | Rate | Excluded frame observations |
|---|---:|---:|---:|---:|
| FY2020 | 1,337 | 2 | 0.15% | 163 |
| FY2021 | 1,394 | 2 | 0.14% | 106 |
| FY2022 | 1,409 | 3 | 0.21% | 91 |
| FY2023 | 1,441 | 35 | 2.43% | 59 |
| FY2024 | 1,458 | 93 | 6.38% | 42 |
| FY2025 | 1,461 | 168 | 11.50% | 39 |

**Validation.** The saved binary panel, annual table and sealed delivery hashes reconcile. These are automated disclosure classifications; independent human semantic validation remains pending. The figure does not identify actual first implementation dates or governance effectiveness.

**Original explanatory wording transferred from the image:**

> Positive Rate = Positive N / Eligible N; Eligible: at least one valid section. Observed-section OR estimate.

## practices/annual_governance_practices_composition_share.png

**Suggested caption:** Composition of disclosed internal AI governance practices, FY2023–FY2025.

**Files:** [PNG](../figures/proposal_academic_v1_20261030/practices/annual_governance_practices_composition_share.png) · [PDF](../figures/proposal_academic_v1_20261030/practices/annual_governance_practices_composition_share.pdf) · [original exploratory PNG](../figures/practices/practice_annual_assignment_share.png).

**Data and period.** [Practice firm-year panel](../data/full_sample/practices/firm_year_practices_panel.csv), [category statistics](../outputs/summary_statistics/practices/practice_category_statistics.csv), frozen [P01–P12 codebook](../config/practices_prompts/codebook.md), and the bundled [native evidence results](../data/full_sample/practices/native/evidence_level_coding.json) and [Practice support quotes](../data/full_sample/practices/practice_quotes.csv). Source run: `implemented-ai-governance-content-v1-20261018`. The displayed sample is restricted to FY2023–FY2025. The source-side data preparation, taxonomy and counting rules are preserved; portable plotting uses bundled native labels and saved statistical controls.

**Measurement and denominators.** Practices are multi-label. A practice assignment is a distinct CIK × fiscal year × practice combination with an existing eligible, source-supported category label. Repeated quotations and support in both Item 1A and Item 7 count once for that practice in the firm-year. For category k and year t, n(k,t) is its distinct firm-year count; A(t) = Σk n(k,t). Each pie reports n(k,t)/A(t). These shares sum to 100% across assignments and differ from n(k,t)/N(t), the prevalence among governance-positive firm-years. A firm-year can contribute several assignments. Unobserved or unresolved categories are not imputed, and firm-years without practice labels do not contribute assignments.

| Fiscal year | Governance-positive firm-years | Firm-years with ≥1 practice | Practice assignments, n |
|---|---:|---:|---:|
| FY2023 | 35 | 32 | 54 |
| FY2024 | 93 | 86 | 135 |
| FY2025 | 168 | 156 | 262 |

**Reconciliation of sample windows.** The original stacked chart covered FY2020–FY2025. Its full-period totals are retained below with explicit scope; they are not totals for the three displayed pies.

| Sample period | Governance-positive firm-years | Firm-years with ≥1 practice | Practice assignments |
|---|---:|---:|---:|
| FY2020–FY2025 (original) | 303 | 281 | 467 |
| FY2023–FY2025 (displayed) | 296 | 274 | 451 |
| FY2020–FY2022 (omitted from pies) | 7 | 7 | 16 |

**Category composition.** The original category names and fixed colors are retained. Zero-count categories remain in the shared legend. Internal percentages are shown for slices of at least 6.7%; smaller slices remain visible and are quantified here. Percentages below are rounded independently.

| Practice | FY2023 assignments / share | FY2024 assignments / share | FY2025 assignments / share |
|---|---:|---:|---:|
| P01 AI governance frameworks, policies, and procedures | 17 / 31.5% | 60 / 44.4% | 117 / 44.7% |
| P04 AI/ML testing, validation, and risk assessment | 8 / 14.8% | 15 / 11.1% | 22 / 8.4% |
| P03 AI use-case review and approval gatekeeping | 7 / 13.0% | 14 / 10.4% | 23 / 8.8% |
| P09 Ongoing AI monitoring, enforcement, and reporting | 7 / 13.0% | 12 / 8.9% | 24 / 9.2% |
| P08 Workforce AI training and awareness | 5 / 9.3% | 12 / 8.9% | 18 / 6.9% |
| P02 Cross-functional AI governance bodies and committees | 3 / 5.6% | 7 / 5.2% | 19 / 7.3% |
| P06 Permissible-use rules and third-party contractual restrictions | 3 / 5.6% | 7 / 5.2% | 16 / 6.1% |
| P05 Model risk management regime for AI/ML models | 2 / 3.7% | 3 / 2.2% | 5 / 1.9% |
| P07 Technical AI access and data-security controls | 1 / 1.9% | 3 / 2.2% | 9 / 3.4% |
| P12 AI regulatory monitoring and adaptation | 0 / 0.0% | 2 / 1.5% | 4 / 1.5% |
| P10 Human oversight and expert-in-the-loop review | 0 / 0.0% | 0 / 0.0% | 5 / 1.9% |
| P11 AI operational pause, safety review, and incident investigation | 1 / 1.9% | 0 / 0.0% | 0 / 0.0% |

**Validation status.** Existing technical/source/aggregation QA is reused: successful non-uncodable evidence, nonempty original quotations, matching TXT hashes and offsets, context inclusion, and equality of evidence assignments, firm-year labels and master statistics. Original-project verification covered 606 practice evidence labels, 284 supporting TXT files and 84 all-period/annual master-statistic cells. The prototype rechecks bundled labels, context quotations and saved counts; only five full section texts are bundled, so the complete TXT-hash recheck remains an inherited original-project result. There is no independent Practice-level semantic QA or human validation. Existing model-review flags remain under the original reporting policy: 23 assignments across FY2020–FY2025 have only flagged evidence; the original evidence review queue contains 134 records and 0 completed human reviews. These full-period QA totals are not presented as FY2023–FY2025-only counts. No new labels or human decisions were created.

**Original explanatory wording transferred from the image:**

> Composition denominator: annual A = sum of validated firm-year–practice assignments; multi-label.

> Total: 467 assignments across 303 governance-Positive firm-years (Item 1A / Item 7). One count per firm-year per practice; all 12 categories retained.

> Shaded FY2020–FY2022: only 2–3 Positive firm-years/year; composition is unstable. Assignment shares differ from firm-year prevalence.

> QA: source quotes and aggregation verified; automated disclosure labels; human semantic review pending.

## size_industry/figure1_annual_positive_rate.png

**Suggested caption:** Annual prevalence of disclosed internal AI governance by market-cap category and GICS sector, FY2023–FY2025.

**Files:** [PNG](../figures/proposal_academic_v1_20261030/size_industry/figure1_annual_positive_rate.png) · [PDF](../figures/proposal_academic_v1_20261030/size_industry/figure1_annual_positive_rate.pdf) · [original exploratory PNG](../figures/governance/size_industry_annual_positive_rate.png).

**Data and period.** [Annual size × sector statistics](../outputs/summary_statistics/governance/size_industry/year_size_sector_statistics.csv) and [firm-year size/GICS metadata](../data/reference/firm_year_metadata.csv), linked to the authoritative [Governance v2 panel](../data/full_sample/governance/combined_firm_year_v2_panel.csv), FY2023–FY2025. All 99 year × size × sector cells are preserved.

**Measurement and aggregation.** Each cell reports positive CIK × fiscal-year observations / valid binary CIK × fiscal-year observations. The observed-section OR rule is unchanged. Missing classifications are excluded rather than filled. Large, Mid and Small denote S&P 500, S&P MidCap 400 and S&P SmallCap 600 membership. Size and GICS sectors use the fixed September 19, 2026 snapshot for every fiscal year, with retrospective membership and survivor-selection limitations.

**Retained data annotations.** Each year is identified above its panel together with its original overall positive/valid count and rate. Cell numerators, denominators, rates and sparsity marks are unchanged. All years retain the original common 0–35% color scale. Hatching and * mark cells with fewer than 20 valid firm-years; † marks fewer than five positive observations, including observed zeros. NA is reserved for cells without valid observations. These marks have no statistical-significance interpretation.

**Validation.** The original project recomputed annual cells with its unchanged `load_analysis()`, `cell_statistics()` and `metrics()` functions. Portable replay reads the same bundled statistics and preserves the original color-scale matrices. Labels remain automated classifications of observed disclosure; independent human semantic validation is pending.

**Original explanatory wording transferred from the image:**

> Cell: Positive Rate (%) and Positive N / Total N. All years share the same color scale.

> * / hatching: Total N < 20.  †: Positive N < 5, including observed zeros.  NA: no valid firm-years.

> Denominator: valid binary firm-year labels within each cell. Fixed size / GICS snapshot: 19 Sep 2026.

> Governance v2 model classifications of observed disclosure; human semantic validation pending.

## size_industry/figure2b_size_sector_exclusion.png

**Suggested caption:** Pooled prevalence of disclosed internal AI governance by market-cap category, with and without Financials and Information Technology, FY2023–FY2025.

**Files:** [PNG](../figures/proposal_academic_v1_20261030/size_industry/figure2b_size_sector_exclusion.png) · [PDF](../figures/proposal_academic_v1_20261030/size_industry/figure2b_size_sector_exclusion.pdf).

**Data and period.** The same [firm-year size/GICS metadata](../data/reference/firm_year_metadata.csv) and [pooled cell statistics](../outputs/summary_statistics/governance/size_industry/pooled_statistics.csv), linked to the authoritative [Governance v2 panel](../data/full_sample/governance/combined_firm_year_v2_panel.csv), pooled FY2023–FY2025.

**Measurement and restrictions.** Each bar is the sum of positive firm-years divided by the sum of valid firm-years, with one count per CIK × fiscal year. Companies may contribute up to three observations; bars do not represent independent company counts or arithmetic means of annual rates. The restricted bars exclude Financials and Information Technology from both numerator and denominator. Large, Mid and Small map to S&P 500, S&P MidCap 400 and S&P SmallCap 600 using the fixed September 19, 2026 membership/GICS snapshot. Missing classifications remain excluded.

**Preserved values.** All-industry counts are 135/1,448, 76/1,166 and 85/1,746; restricted counts are 54/1,022, 41/836 and 57/1,203, in Large/Mid/Small order. The corresponding restricted rates remain 5.28%, 4.90% and 4.74%. The original grouped-bar type and all six value annotations are retained.

**Validation.** The original project used its unchanged `metrics()` function. Portable replay reconstructs the same pooled numerators and denominators from the bundled size-by-sector statistics. Underlying results remain automated disclosure classifications with independent human semantic validation pending.

**Original explanatory wording transferred from the image:**

> FY2023–FY2025 pooled firm-years: all industries and excluding Financials / Information Technology

> Rate = pooled Positive N / pooled valid binary firm-years; labels show Positive N / valid N.

> Each CIK × fiscal year is counted once; firms may contribute up to three observations. Missing classifications are excluded.

> Fixed index-membership / GICS snapshot: 19 Sep 2026. Governance v2 disclosure labels; human semantic validation pending.

## Reproduction and preservation

From the prototype root, run `python -B scripts/plot_figures.py`. The supported
adapter reproduces the eleven currently selected PNGs from bundled inputs,
including the four academic panels, and writes replay products only under
`outputs/reproduced/`. The four updated panels also have vector PDF companions.
Normal replay requires no original-project directory, source TXT corpus, API
credentials or model inference. Historical drawing references and classification
functions remain unchanged. The original ten-figure provenance is retained in
`figure_sources.json` and the previous delivery manifest; the presentation overlay
is recorded in `figure_presentation_updates.json`.
