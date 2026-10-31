# Version and source audit

Audit date: 29 October 2026. The audit preceded copying. Selection used run records, frozen standards, code/configuration hashes, completed coverage and downstream input hashes. File modification times were not used to rank versions.

Presentation update, 30 October 2026: four academic proposal panels were added as byte-identical PNG/PDF copies under `figures/proposal_academic_v1_20261030/`. The current figure registry selects eleven views: seven historical figures and four academic panels. The three-year Practice pies contain 451 assignments (54, 135, 262), while the full FY2020–FY2025 result remains 467. All ten historical figure assets, frozen classifiers, data, prompts and statistical tables are retained unchanged. The presentation overlay, external notes and separate replay evidence document this update; the previous delivery and source manifests are preserved under `docs/provenance/proposal_presentation_update_20261030/`.

## Selected binary delivery

| Attribute | Audited value |
| --- | --- |
| Original bundle | `outputs/full_universe_implemented_internal_ai_governance_v2/` |
| Prompt / classification version | `implemented-internal-ai-governance-v2.0` |
| Recorded start | `2026-10-13T08:45:17.873118+00:00` |
| Recorded standalone Run ID | Absent from the original manifest; no synthetic value inserted into the data |
| Completion evidence | Run status complete; delivery status complete; delivery QA passed |
| Main result | `combined_firm_year_v2_panel.csv`, SHA-256 `dc4b64256cbf72caf5c7bc425fc5daeacf36896b59f2109af97976c6d0237849` |
| Final coverage | 8,500 classified firm-years, 500 separate exclusions; 303 Positive, 8,197 Negative; 16,222 classified sections |
| Main + recovery prompt versions | 16,143 main, 56 recovery-1, 23 recovery-2 classified sections |

The final panel is the firm-year result. Section exports are retained as inputs and evidence rather than substituted for the panel. The saved delivery manifest covers 18 artifacts, all of whose current hashes match. Later Governance figures cite this same panel hash.

### Historical code lineage

The run bundle's `code_snapshot/governance_v2.py` is an execution-stage snapshot, hash `3ae1a27f...15844f`. Subsequent recovery and final delivery changed the final aggregation/QA code. The final delivery manifest explicitly records final code hashes:

| Module | Final delivery SHA-256 |
| --- | --- |
| `governance_v2.py` | `6d3f4da867dcb5d365b6558a16c9d45534bea126a082c0de0718d605632f30ad` |
| `governance_v2_recovery.py` | `f68a82f05d0ccc98c9b5286e03ee8bec8216ac26d702ff4b503463f4a6cbf259` |
| `governance_v2_delivery.py` | `1fb6c3a605053a9592ff7d5cc19463f596623c134673cc292f0a5163df3aef9b` |

The copies in `tmp/deepseek_global_config_20261025/before/src/ai_restrictions/` match all three hashes. They are therefore the selected final historical modules. The historical client and prompt come from the original run snapshot; supporting imports come from the pre-update source snapshot. The portable adapter supplies relocated paths and validates the final aggregate against the entire saved panel.

The live shared client was changed on 25 October to explicit enabled thinking and high reasoning effort, omitting temperature. Using that client would misdescribe this completed historical run. Separate historical clients and saved configurations preserve the actual request parameters.

## Selected Practices delivery

| Attribute | Audited value |
| --- | --- |
| Original bundle | `outputs/implemented_ai_governance_content_analysis/` |
| Recorded Run ID | `implemented-ai-governance-content-v1-20261018` |
| Prompt version | `implemented-ai-governance-content-v1.0` |
| State directory | `data/interim/classifications/implemented_ai_governance_content_analysis/v1/` |
| Frozen time | `2026-10-18T08:01:47.017110+00:00` |
| Codebook SHA-256 | `eb145750b1b3169aa1c372395d1810cbe0ff9008175325f261bd39b58753a698` |
| Native firm-year result SHA-256 | `3f13876a0144b85509efdd0d0e7fbec7606161f7acbc7f4ef11d02e9b7909253` |
| Coverage | All 303 binary Positive firm-years; 403 evidence units; 12 practice categories |
| Validation status | Automatic integrity passed; human semantic validation pending |

All 81 original delivery-manifest file hashes match. The native code snapshot matches the manifest, including the core content-coding module, reporting module, client and prompt. The primary Practices CSV is an explicit column projection of the native final panel and retains all 303 rows. Native joint outputs are retained unchanged to reproduce the original aggregation and schema checks.

The 26 October Practice visualization uses this same frozen run and codebook. Its annual assignment-composition statistics do not constitute a new classification version. No later completed, separately validated P01–P12 classification superseding this frozen run was identified in the audited project.

### Saved template versus actual runtime message

The Practice bundle's saved `user_prompt_template.txt` appends `Return the required JSON for this evidence_id.` after the evidence object. The frozen `closed_coding` implementation assembles the user message inline and omits that last line. An original saved request confirms the inline implementation. The artifact preserves the snapshot unchanged, adds the exact runtime scaffold and retry suffix extracted from source, and includes a byte-identical original request. The actual payload SHA-256 is `8b0388e78c5169366d8051902fb0300e038b71e684d01f806effa0bdd81e65ce`. This documentation discrepancy is resolved explicitly; the templates are not silently treated as identical. See `outputs/validation/prompt_rendering_audit.json`.

## Other versions and excluded material

| Existing material | Treatment and reason |
| --- | --- |
| Fixed-sample implemented-governance v1 and full-universe v1 | Earlier definition/pipeline; superseded for this binary measurement. Classification data and old subtype charts excluded. Small legacy modules remain only where required by the frozen v2 import graph. |
| Item 7 implemented-governance v1 | Earlier section-only measurement. Its run metadata was the historical configuration source; its labels are not merged into v2. |
| G1/G2/G3/R1/R2 subtype visualizations | Incompatible with the binary-v2 construct and P01–P12 inductive practices; excluded. |
| Preliminary open-coding labels and draft codebooks | Development history; excluded from final classifications. The development sample, frozen method, refinement audit and final prompts preserve relevant lineage. |
| Pro-AI Orientation, Governance Purpose, temporal/adoption/position analyses | Outside this artifact's measurement scope; their datasets and analytical modules excluded. |
| 28 October size/industry pie variants | Same source measurement; the selected stacked bars provide a compact comparison. Reformatting did not supersede their data. |
| Bulky caches, raw API responses and complete request payloads | Remain in the original project. Final successes, complete failure-event views, original log hashes, recovery records and accounting are bundled. |

## Figure lineage and checks

The selected figures draw from binary v2 and the frozen Practice run only. Four downstream visualization manifests have matching classification-source hashes. Independent recalculation matched 18 size-composition cells, 33 industry-composition cells, 99 Size × Industry cells, 84 Practice prevalence cells and 72 Practice assignment-composition cells. The latter count distinct firm-year–practice assignments.

The original 18 October frequency and annual-prevalence figures remain valid because their underlying classification was unchanged. The 26 October assignment-composition figures add a different denominator; they do not replace prevalence. Three complementary 28 October Size × Industry figures retain annual rates, endpoint changes and pooled rates.

## Recorded issues and handling

1. **Coverage estimator differs from the guideline's strict default.** The source workflow explicitly adopts observed-section OR. All delivered labels are preserved; 761 single-section negatives are marked by coverage fields and discussed prominently.
2. **No standalone binary Run ID field.** The manifest retains this absence. Bundle identity, recorded start, prompt version and file hashes jointly identify the selected run.
3. **Human semantic validation remains open.** The Practices run has 134 pending evidence records. No current project review database was found at its configured path during audit; the copied panel records every firm-year as `not_reviewed`.
4. **Shared native Practice schema.** Three-dimensional native material is an unavoidable dependency of the existing validator and union function. P01–P12 views and selected figures define the artifact's research scope; later Purpose modules are absent.
5. **External full-source and API state.** Five native text sections and all bounded Practice contexts are included. Full text acquisition/extraction and fresh paid inference were not reproduced.
6. **Fixed metadata timing.** Size/GICS labels use the 19 September 2026 retrieval snapshot retrospectively. The snapshot supplies no annual historical membership or effective-date series.
7. **Practice user-template snapshot differs from runtime assembly.** Both are retained, with an exact saved request and original code establishing the runtime message. The source snapshot is not overwritten.

There is no unresolved file-hash conflict in the selected final datasets. These substantive scope and validation limits remain explicit in the artifact. Machine-readable evidence is in `outputs/validation/project_audit_20261029.json`, `figure_audit_20261029.json`, original run records and the final source manifest.
