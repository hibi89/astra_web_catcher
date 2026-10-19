# ASTRA p4 — two documented mechanism contract review v0.1

## Scope and reason

Two independently authored local demos now exist on the feature branch:

| ID | Public publisher reference | Input | Locally implemented trigger | Locally implemented outcome | Transport |
| --- | --- | --- | --- | --- | --- |
| `text_form` | Selenium Web form + first-script tutorial | `my-text` | `submit` | `Received!` | **own** local `POST /submit` |
| `checkbox` | Selenium inputs example + interactions tutorial | `checkbox_input` | `change` | `Checked / Unchecked` | **own** DOM event only |

Common *schema fields* are `input`, `trigger`, `local_output`, and `evidence_level`. These are **not automatically interchangeable mechanisms**: HTTP form submission and DOM state toggling are kept separate. No parser accepts arbitrary external URLs or newly inferred site behavior.

The `astra_contracts/mechanism_contract_review.py` reviewer only reads the two source modules and their three human-curated public-reference excerpt files. Expected source **Git blob SHA-1** and evidence **SHA-256** values are explicitly pinned. It emits a JSON review report to stdout only when both contracts pass checks. Missing, changed, oversized, symbolic-linked, escaped or relabeled inputs fail closed without an approval report. The tool does not import/execute source modules or embedded evidence, perform network access, open a browser, write files, regenerate demos, authenticate users or deploy.

## Design alternatives

- **Static JSON contract table only**: cheapest and simplest, but drifts silently from source and evidence. Rejected.
- **Executable read-only reviewer with pinned files**: lightweight local filesystem read, zero API/model cost, source/evidence change detection and negative tests. Chosen for safer reuse.

This is a review contract, not a generalized generator, extraction engine, UI-equivalence score or owner-database permission system.

## Reproduction and measured testing

From a **complete checkout** of the feature branch:

```bash
python -m astra_contracts.mechanism_contract_review
python -m pytest -q tests/test_mechanism_contract_review.py tests/test_public_checkbox_analogue.py
python -m compileall -q astra_contracts tests
```

Actual this-unit isolated workspace: **22/22 new contract pytest PASS** plus **11/11 existing checkbox pytest PASS = 33/33**, Python 3.13.5 and compileall PASS. Positive fixture tests use synthetic files with computed hashes; current real checkbox source and evidence hashes have dedicated tests. The new source and test files were re-fetched from GitHub and their blobs matched tested local files byte-for-byte. The publisher form source blob and both excerpt SHA-256 constants were checked from previously retrieved repository contents. **The default CLI on a full feature-branch checkout was not run here**, because the local workspace only contains the checkbox source plus selected fixtures; the full previous 739-case regression suite was not rerun.

If `python -m astra_contracts.mechanism_contract_review` fails on a complete checkout, verify the checked-out branch and hashes; do **not** automatically update expected digests or treat a mismatch as authorization to regenerate/overwrite original data.

## Authority boundaries

- Source file integrity **is not** source-site authenticity.
- Manually curated publisher text **is not** captured live click evidence, trusted screenshots, semantic equivalence or the original HTTP method.
- `local_functional_demo=true` means prior isolated demo tests; this audit does **not** execute either app or browser.
- All original-site behavior and live-interaction flags remain false.
- `review_state=review_only_no_approval`, `generation_contract=blocked_pending_review`.
- Customer DB/API, original source code, credentials, Vercel and deployment untouched. No Actions run.
- Existing feature implementations, main branch and source database remain unmodified.

## Next bounded unit

Prefer a genuinely usable, authorized browser to capture **one** original-reference before/after interaction with provenance. The available Chat-mode Browser connector is **read-only** (tab listing/content); it cannot perform a click. Do not retry administrator-blocked Chromium unchanged. If a genuine interaction cannot be acquired, continue with a user-owned schema interface / evidence intake only after confirming an authorized schema source, instead of inflating progress via more fictional widgets.

**Overall conservative progress ~49%, unchanged.** Actual arbitrary URL→owner DB/API→production app remains unproven.
