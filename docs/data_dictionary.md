# Data dictionary

Read CIKs as strings to preserve leading zeros. Fiscal year is the company's fiscal-year attribution in the source panel. Native CSVs are byte-identical copies; primary Practice and figure views explicitly project existing rows or columns. JSON arrays stored in CSV cells require JSON parsing.

## Main data tables

| Table | Unit and rows | Interpretation |
| --- | --- | --- |
| `data/full_sample/governance/combined_firm_year_v2_panel.csv` | 8,500 eligible CIK × FY | Final delivered binary labels and section provenance |
| `data/full_sample/governance/exclusion_manifest.csv` | 500 excluded frame firm-years | Both sections unavailable; binary label blank |
| `data/full_sample/governance/item1a_v2_classification_results.csv` | 9,000 frame sections | 8,195 classified; 805 unavailable |
| `data/full_sample/governance/item7_v2_classification_results.csv` | 9,000 frame sections | 8,027 classified; 973 unavailable |
| `data/full_sample/governance/input_manifest.csv` | 18,000 frame sections | Frozen classified-input identity, hashes and source gates |
| `data/full_sample/practices/firm_year_practices_panel.csv` | All 303 Governance-Positive CIK × FY | Primary P01–P12 multi-label view; 28 columns |
| `data/full_sample/practices/evidence_level_practices.csv` | All 403 evidence units | Practice assignments, sources and uncertainty flags |
| `data/full_sample/practices/practice_quotes.csv` | 606 evidence–practice label records | Exact support for 467 distinct firm-year–practice assignments |
| `data/full_sample/practices/native/` | Original shared content outputs and inputs | Unmodified source of primary Practice views; includes native joint dimensions |
| `data/reference/firm_year_metadata.csv` | 9,000 frame rows | Fixed size/GICS attributes; six missing-CIK rows remain in frame audit |

CIK × FY is unique in the eligible Governance panel and the Practice panel. The complete frame has 8,994 nonempty unique CIK × FY pairs and six missing-CIK records for one firm. Missing identities remain excluded; they are not fabricated or resolved by this assembly. Evidence IDs are unique in the 403-row evidence input and coding tables.

## Governance panel fields

| Field or family | Values / meaning |
| --- | --- |
| `cik`, `ticker`, `company_name`, `fiscal_year` | Source identity; CIK × FY is the main research key |
| `implemented_internal_ai_governance_v2` | `1` Positive; `0` Negative under the delivered observed-section estimator; blank for excluded/unresolved states |
| `classification_status` | `complete` for all 8,500 eligible rows; `excluded_double_unavailable` for the separate 500-row exclusion table |
| `exclusion_reason` | Source reason for exclusion; never interpreted as Negative |
| `observed_section_count` | Number of valid observed sections: 0, 1 or 2 |
| `source_status` | `both_observed`, `single_section_observed`, or `double_unavailable` |
| `accession_consistent` | Whether populated section accessions agree; blank if comparison unavailable |
| `valid_section_accession_conflict` | Source conflict gate; Boolean, preserved from final aggregation |
| `item1a_text_available`, `item7_text_available` | Boolean source-gate results |
| `item1a_v2_classification`, `item7_v2_classification` | Section `Positive` / `Negative`, blank if unavailable or unresolved |
| `item1a_evidence`, `item7_evidence` | JSON arrays of original binary evidence quotations |
| `item1a_source_reason`, `item7_source_reason` | Source/extraction exception explanations |
| `item1a_accession`, `item7_accession` | Original filing accession numbers |
| `item1a_filing_date`, `item7_filing_date` | Native filing dates; formatting can differ (`YYYY-MM-DD` versus `YYYYMMDD`) |
| `item1a_fiscal_year_end`, `item7_fiscal_year_end` | Native fiscal-year end, when available |
| `item1a_text_path`, `item7_text_path` | Original project-relative classified text path; most full texts are external to this artifact |
| `item1a_sha256`, `item7_sha256` | SHA-256 of original text bytes |

A Negative label indicates no qualifying evidence in the observed disclosure. For 761 negatives only one target section was observed. Source coverage is a necessary qualifier when using that variable. Blank labels, exclusions, section unavailability and historical request failures are distinct states.

Section exports additionally retain `input_file`, `input_sha256`, `classification`, `evidence_locations`, `prompt_version`, `model`, `classified_at_utc`, `manual_review_needed`, `review_reason`, `reason`, `mechanism_summary`, `scope_limitation` and `temporal_basis`. Evidence locations are 0-based half-open character intervals in Python's newline-normalized Unicode text, rather than byte offsets or original filing page numbers.

## Practice panel fields

| Field or family | Meaning |
| --- | --- |
| Identity and `sector` | CIK, ticker, company name, fiscal year and the existing fixed sector label |
| `positive_binary_v2` | `1` for every row; this dataset conditions on original Governance positivity |
| `evidence_n` | Original evidence units linked to the firm-year |
| `coded_evidence_n` | Structured final evidence results, including explicitly uncodable results |
| `failed_evidence_n` | Final failed/not-submitted units; zero in this delivery |
| `uncodable_evidence_n` | Units whose supplied content cannot be sufficiently coded |
| `flagged_evidence_n` | Units with the model's review flag |
| `emerging_evidence_n` | Units with a proposed emerging theme in the native joint schema |
| `source_items` | JSON array of Positive source chapters |
| `coding_status` | `complete` (245 rows) or `complete_with_review` (58 rows) |
| `human_review_status` | `not_reviewed` for every row |
| `practices_categories` | JSON array of assigned frozen Practice IDs |
| `P01`–`P12` | 1 if at least one existing evidence result assigns that practice, otherwise 0 |

Zeros record the absence of an assigned category in supplied evidence/context. Uncodable and review flags qualify that absence. Twenty-two all-zero Practice rows remain Governance Positive. The dataset supplies no Practice labels for the 8,197 Governance-Negative firm-years or the 500 excluded firm-years.

## Frozen Practice IDs

The original definitions, inclusion/exclusion boundaries and examples are in `config/practices_prompts/codebook.md` and `.json`. The following names are copied from that codebook; these counts use all 303 Positive firm-years as denominator.

| ID | Frozen category name | Firm-years |
| --- | --- | ---: |
| P01 | AI governance frameworks, policies, and procedures | 195 |
| P02 | Cross-functional AI governance bodies and committees | 29 |
| P03 | AI use-case review and approval gatekeeping | 47 |
| P04 | AI/ML testing, validation, and risk assessment | 51 |
| P05 | Model risk management regime for AI/ML models | 13 |
| P06 | Permissible-use rules and third-party contractual restrictions | 26 |
| P07 | Technical AI access and data-security controls | 13 |
| P08 | Workforce AI training and awareness | 35 |
| P09 | Ongoing AI monitoring, enforcement, and reporting | 46 |
| P10 | Human oversight and expert-in-the-loop review | 5 |
| P11 | AI operational pause, safety review, and incident investigation | 1 |
| P12 | AI regulatory monitoring and adaptation | 6 |

Practice labels are multi-label and have no separate Explicit/Implicit field. `explicitness` in the native quote table is blank for practices; the native motivation/vision dimensions use different fields. No Practice maturity score or hierarchical scale is constructed.

## Evidence and source fields

`evidence_id` links native coding, evidence units, quote records and the pending review queue. `section`, `accession_number`, `filing_date`, `input_file` and `input_sha256` preserve filing/text identity. `evidence_start` / `evidence_end` locate the focal source span. `context_blocks` contains continuous same-chapter blocks with original offsets. `practices` is a JSON array of category objects with `category_id`, `quote`, `explanation` and `quote_locations`.

`binary_original_evidence`, `binary_location_method` and `source_span_restored` preserve the 17 normalization restorations in the derived content inputs. `uncodable`, `review_flag`, `review_reason`, `coding_status`, `returned_model`, `codebook_sha256`, `prompt_version` and `human_review_status` retain automated coding and validation status. Native joint emerging-theme details remain in `native/evidence_level_coding.json`.

`data/reference/source_manifests/` contains the owning upstream Item 1A / Item 7 manifests, including original filing URLs where supplied, accession numbers, raw-source paths/hashes, extraction methods and retention status. Blank source URLs, including SRAF-based Item 7 records, remain blank. The frozen Governance `input_manifest.csv` is authoritative for the bytes actually classified. A retained locator or hash does not imply that the corresponding raw 10-K file is bundled or still retained upstream.

## Statistics and provenance fields

`positive_rate` and `assignment_share` are fractions from 0 to 1. Fields ending `_pct`, `percentage` or `assignment_percentage` are percentages from 0 to 100. Fields ending `_pp` are percentage-point differences. Counts and denominators are stored separately. `source_manifest.csv` records original paths, hashes, selection rationale and transformation scope for every delivered artifact. `schema_inventory.csv` lists columns and row counts for the data, statistics and audit CSV tables; catalogue/provenance indexes are excluded. Native data are not recoded.

Historical failure-event counts refer to request/validation events, often involving retries for the same section. They are not final missing or failed firm-year counts. Empty final exception/failure CSVs retain their headers and remain part of the bundle.
