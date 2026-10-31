# Full-universe binary v2 workflow

Authority: `docs/implemented_internal_ai_governance_v2.md`. This entry point reads saved
Item 1A and Item 7 section text, makes fresh full-text DeepSeek calls, and aggregates
the observed-section OR estimate expressly requested for this run.

```powershell
.venv/Scripts/python.exe scripts/39_classify_governance_v2.py --stage prepare
.venv/Scripts/python.exe scripts/39_classify_governance_v2.py --stage pilot --workers 64
.venv/Scripts/python.exe scripts/39_classify_governance_v2.py --stage full --workers 64
.venv/Scripts/python.exe scripts/39_classify_governance_v2.py --stage report --workers 64
.venv/Scripts/python.exe scripts/40_recover_governance_v2.py --retry --workers 16
.venv/Scripts/python.exe scripts/40_recover_governance_v2.py --retry --round 2 --workers 8
.venv/Scripts/python.exe scripts/39_classify_governance_v2.py --stage report --workers 64
.venv/Scripts/python.exe scripts/41_verify_governance_v2_delivery.py
```

`full` verifies the actual four-record pilot before continuing. Validated v2 successes
and material-review responses are skipped on resume; failures have finite request
limits. Source, prompt, standard and LLM configuration changes are rejected on resume.
`report` rebuilds the CSV deliverables, QA and PNG/PDF figures from saved v2 caches
without paid calls. Network access and a configured `DEEPSEEK_API_KEY` are required
only for pilot/full calls. The existing `.env` resolver and DeepSeek client are reused.

The isolated run bundle is `outputs/full_universe_implemented_internal_ai_governance_v2/`,
as explicitly requested. Source manifests, text and v1 output trees remain protected.
This bundle contains model classifications, source/LLM exception manifests, reproducible
request/response snapshots and provisional analysis artifacts. It does not write human
review decisions or silently promote a formal processed research dataset.

Recovery calls reuse the identical v2 System Prompt and model settings. They add
saved, separately versioned user suffixes and permit at most two corrective rounds;
successful records are never repurchased. Typography and paired pagination headers
are aligned only when all substantive words match uniquely, and the saved evidence
restores the complete exact source span. Any individually verified page-only
override has its own source-hash/offset audit. No semantic paraphrase is silently
accepted. A provider HTTP 402 triggers a queue circuit breaker; funded resumes
retain already validated results and retry only unresolved inputs.

Item 1A original automatic-pass and independently verified text are eligible. Saved
`repaired_verified` secondary texts can be used with their explicit path/hash lineage.
Later review-repair findings override older flags. Unresolved selection/boundary cases,
unverified repair candidates and incorporated pointers lacking the actual text stay
unavailable. Item 7 uses the latest v2.4 successful automatic-pass manifest.

Positive in either observed section yields 1. Without a Positive, any unresolved LLM
error/review/pending status blocks 0. One observed Negative plus unavailable other
section yields 0 under the user-selected observed-section estimator; coverage flags
retain that distinction. Only double unavailable valid text is excluded. Cross-filing
accession conflicts between available sections remain review cases.

`requests/*.json` contains the exact system/user messages and API payload without
credentials. `responses/*.json` preserves every received response, including malformed
or truncated responses. `request_manifest.jsonl` identifies each transport attempt,
payload digest, response snapshot, model, token usage when provided, and outcome.
`cache/*.json` holds source-linked validated results and quote offsets. The frozen
standard/prompt/configuration and execution code snapshots make the requests auditable.

Annual rates are withheld for years with unresolved eligible observations. Counts of
already identified positives can be plotted provisionally with that label. Once all
eligible values are valid binary results, rates use Positive N / Eligible N. Monetary
cost stays unavailable unless a verified price snapshot is added explicitly; token
counts use only API-returned usage.
