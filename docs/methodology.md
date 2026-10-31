# Measurement methodology

This document describes the selected completed measurement. The frozen guidelines and prompts are authoritative; the portable adapters preserve their classification and aggregation logic.

## Binary Governance v2

The construct is disclosed evidence of an implemented internal AI governance arrangement. At least one connected practice must meet all five conditions: internal organizational scope, explicit application to AI, an established or executed arrangement, an identifiable governance mechanism, and traceable evidence. Risk awareness, ordinary adoption, prospective plans, generic controls, external regulation and bare use restrictions without additional governance evidence do not independently qualify. These are the project's operational rules; the guideline uses NIST AI RMF as a conceptual reference.

Saved source manifests identify company, CIK, fiscal year, accession, filing date, extraction status, source text path and SHA-256. The existing source gate selects valid saved Item 1A / Item 7 text, retaining extraction and source exceptions. The complete available section is sent to the model; keyword screening is disabled. Upstream acquisition and extraction were not rerun for this artifact.

The original binary client requests `deepseek-flash` (`DeepSeek-V4.1-Flash` was the intended version), `temperature=0`, `max_tokens=16384` and JSON-object output. Thinking and reasoning effort were not explicitly set. Timeout is 120 seconds; transport has at most three attempts with the saved retry policy. Main-run concurrency was 64; corrective rounds used 16 and 8 workers. The frozen configuration files preserve these distinctions. The provider's model alias is not a permanent immutable model identifier.

The full system prompt incorporates the complete standard, including its hypothetical examples. There are no separate runtime few-shot messages in this binary workflow. `user_prompt_template.txt` includes source identifiers and the complete section text.

The response has exactly eight substantive fields: `classification`, `evidence`, `reason`, `manual_review_needed`, `review_reason`, `mechanism_summary`, `scope_limitation`, and `temporal_basis`. Positive requires locatable supporting evidence and a mechanism summary. Material ambiguity requires a null classification and a review reason. The historical quote locator can recognize normalized whitespace/case matches; these locations and the original quotation are preserved. Two bounded corrective rounds addressed validation failures without changing the binary definition.

### Firm-year aggregation and coverage

The delivered run explicitly adopts the **observed-section OR estimate** described by its workflow:

- Any classified Positive section yields Positive, subject to the accession-conflict rule.
- A pending, failed or review section without a determining Positive leaves the firm-year unresolved.
- Two unavailable sections produce a separate exclusion with a blank binary value.
- Available classified sections with no Positive yield Negative, including a single observed Negative section with an unavailable companion.

The frozen conceptual guideline also specifies a stricter complete-two-section rule for negative evidence. The source workflow expressly selects the observed-section alternative. Both documents are retained; the artifact preserves the delivered labels and exposes coverage rather than silently applying a different estimator.

Final counts are 8,500 classified firm-years and 500 double-unavailable exclusions. There are 7,722 two-section and 778 single-section classified firm-years; the latter contain 17 Positive and 761 Negative labels. There are no final unresolved eligible observations. The two section exports retain all 18,000 potential section records, including 1,778 unavailable sections. Historical request failures remain a separate event history.

## Inductive Governance Practices

The selected practice coding is the completed frozen content-analysis run `implemented-ai-governance-content-v1-20261018`. Its original taxonomy was developed through LLM open coding of 50 maximum-variation firm-years and 73 evidence units, using seed 42. A context supplement covered 21 of those firm-years and 38 evidence units. Definitions, neighboring-category boundaries and examples were then frozen. The taxonomy contains 12 practices; the native joint codebook also contains nine motivation and nine vision categories. The primary artifact variables are P01–P12.

The full coding population is all 303 original Governance-Positive firm-years: 306 Positive chapters and 403 evidence units. Each unit contains a focal Governance quotation and bounded context extending 1,100 characters on each side of the relevant quotations. Overlapping same-chapter blocks are merged, and companion Positive evidence in that chapter is supplied. This stage does not search negative sections or reread whole filings to discover additional governance disclosures.

Seventeen original binary quotations with whitespace/case normalization were restored to the exact source span in these derived content inputs. `binary_original_evidence`, the location method and restoration flag preserve this transformation; source text bytes and binary labels remain unchanged.

Closed coding reapplies the frozen codebook to all 403 units, including the development sample. A practice label requires a supported implemented arrangement, a valid frozen category ID, an exact continuous quotation within one supplied context block and an explanation. Emerging themes and uncertainty trigger review; they do not automatically create new categories. Practice labels have no separate Explicit/Implicit variable. The original joint schema and validator require the other native dimensions, so the unmodified native codebook and source results remain available as reproduction dependencies.

The saved `user_prompt_template.txt` is a readable scaffold with an extra final Return instruction. The actual `closed_coding` function assembles the canonical codebook and evidence input inline without that final line. The artifact preserves both the original saved scaffold and the exact `runtime_user_prompt_template.txt`, together with the original finite validation-correction suffix. An unchanged saved AXP FY2020 Item 7 request is bundled and matches the reconstructed runtime payload and its hash exactly. The saved system prompt matches the runtime system string.

Practice requests retain the same saved alias, temperature, output budget and JSON format as the binary workflow, with 16 workers. Thinking was unspecified. The source configuration records provider alias drift on 18 October; it is preserved as historical metadata. A 65,536-token exception applied only to the earlier codebook-synthesis step, not full-sample evidence coding. The original practice client adds HTTP-exception handling; its request generation parameters match the historical binary client. Both clients are copied separately.

### Practice aggregation

The original deterministic function unions category IDs across all evidence and sections within CIK × fiscal year. Each practice contributes at most one assignment to a firm-year. It retains all 303 Positive firm-years and their evidence counts, failed/uncodable counts, flags and human-review status.

There are 467 distinct assignments supported by 606 evidence-label quote records. The panel contains 281 firm-years with at least one practice, 107 with multiple practices, and 22 without an observed practice assignment. The latter remain Governance Positive. All P01–P12 zeros mean no assigned label in the supplied evidence/context; uncertainty fields qualify the completeness of that absence.

All 403 units have a structured final result: 369 are coded and 34 are marked uncodable. Seventy-seven carry a model review flag; these states overlap and are not disjoint categories. The final evidence-failure count is zero. Main statistics retain the source delivery's supported labels, including 23 assignments supported only by flagged evidence. They have not been independently human validated.

## Figure estimands

The annual Governance rate is Positive firm-years divided by eligible classified firm-years. Size and industry composition instead divide a subgroup's Positive count by all Positive firm-years in that year. Size × Industry rates use the valid classified firm-years within the relevant cell; pooled rates use summed firm-year counts across FY2023–FY2025. Changes are percentage-point differences between existing annual rates.

Practice prevalence divides the number of Positive firm-years assigned a practice by all Governance-Positive firm-years in scope, including zero-assignment and review observations. Practice assignment composition uses the sum of distinct firm-year–practice assignments as its annual denominator. Multi-label prevalence can sum above 100%; assignment shares sum to 100%. The [figure registry](figure_registry.csv) records each selected figure separately.

## Quality control and interpretation

The assembly verified the original delivery hashes, CIK × fiscal-year keys, full sample coverage, observed-section OR labels, evidence-to-panel unions and selected figure statistics. It also checked all 306 Positive source file hashes, 403 exact evidence anchors and 606 practice quote locations against the original TXT files. Portable replay validates all 403 native evidence results against their bundled contexts and reproduces both final panels using the original aggregation functions.

These checks establish file integrity, traceability and deterministic consistency. Independent human semantic accuracy, intercoder agreement, extraction-boundary accuracy and governance effectiveness remain outside the completed validation. The inherited review queue contains 134 pending evidence records and no completed human decisions. Fixed size/GICS snapshot timing, source coverage and small early-year Positive samples constrain interpretation.
