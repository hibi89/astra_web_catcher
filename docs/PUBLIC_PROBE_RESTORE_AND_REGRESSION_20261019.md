# ASTRA p4 — public-reference code restore and complete segmented regression (2026-10-19 KST)

## GitHub restoration (verified)

- Previous HEAD: `7bad9ef36078c56069f192917799922543f0f7c8`.
- Restored all **9 previously uncommitted files**, functional commit `57465a31f2837086d01050293d098007f8b4069d`: `astra_contracts/public_reference_probe.py`, `scripts/selenium_public_form_capture.py`, both `tests/test_public_*.py`, `docs/PUBLIC_REFERENCE_PASSIVE_PROBE_V01.md`, and four `fixtures/public_selenium_*` evidence/contract files.
- All **9/9 Git blob SHAs match** the local original versions. Content fetched again from the remote feature branch after committing.
- `docs/PUBLIC_REFERENCE_PASSIVE_TRIAGE_20261019.md` now has an addendum explicitly superseding its old "source was not pushed" limitation.

## Locally executed tests (disjoint partitions)

Environment: Python **3.13.5**. Collected `python -m pytest --collect-only -q tests` → **716 tests**. Reran the entire exact set as eight non-overlapping CLI invocations to avoid long-running generated-app fixture timeouts:

| Partition | Files | Result |
| --- | --- | --- |
| Core and provenance | `test_capture_claim_review.py`, `test_capture_intake.py`, `test_capture_transition_ledger.py`, `test_data_mapping.py`, `test_evidence_claim_levels.py`, `test_evidence_integrity.py`, `test_functional_spec.py`, `test_generation_contract.py`, `test_jp_nail_archive_conversion.py`, `test_observation_contract.py`, `test_public_form_browser_plan.py`, `test_public_reference_probe.py`, `test_reviewer_decisions.py`, `test_review_transfer.py` | 333/333 PASS |
| Acceptance and synthetic core | `test_feature_acceptance_adapter.py`, `test_manual_trace_pipeline.py`, `test_observed_ui_mapping.py`, `test_synthetic_bridge.py`, `test_synthetic_crud.py`, `test_synthetic_acceptance.py`, `test_synthetic_generator.py`, `test_schema_query_extension.py` | 203/203 PASS |
| Schema reuse and CRUD embed | `test_schema_reuse_adapter.py`, `test_schema_crud_embed.py` | 57/57 PASS |
| Query embed | `test_schema_query_embed.py` | 24/24 PASS |
| DOM and standalone review | `test_mapping_review_dom_simulation.py`, `test_transition_review_dom_simulation.py`, `test_ui_dom_simulation.py`, `test_review_ui.py` | 25/25 PASS |
| Query UI | `test_schema_query_ui.py` | 23/23 PASS |
| Mapping review UI | `test_mapping_review_ui.py` | 20/20 PASS |
| Transition review UI | `test_transition_review_ui.py` | 31/31 PASS |
| **Total** | **All 32 test files, exactly once across partitions** | **716/716 PASS** |

`python -m compileall -q astra_contracts scripts tests` → PASS.

Offline application checks: `python -m astra_contracts.public_reference_probe fixtures/public_selenium_form_note_20261019.json fixtures/public_selenium_form_page_excerpt_20261019.txt fixtures/public_selenium_official_docs_excerpt_20261019.txt` → PASS, report marks `live_browser_click_verified=false`. `python scripts/selenium_public_form_capture.py` → dry-run only, `browser_launched=false`, `network_used=false`.

One preexisting unrelated HTTPX DeprecationWarning occurred; no test failures.

## Hard evidence and authorization limits

These tests establish the *offline module and existing synthetic app regressions*, not a successful live site click, screenshot authenticity, real database authority, general-purpose website reconstruction, or production readiness. The public Selenium form page was only read passively in the previous step; publisher documentation describes expected behavior. No browser has been launched for the public smoke test in this recovery, the formerly administrator-blocked browser was not retried, and no GitHub Actions were consumed. The `GenerationContract` remains `blocked_pending_review`. The protected `main` commit `dc23ee604d02513c890615a3a98440c1ea8a5270` and all customer DB/API content remain unchanged.

Next action: use a genuinely permitted browser environment for **one** public Selenium demo click and collect first-hand before/after evidence, or leave the claim explicitly unverified; never promote an archived or fake-driver result into first-hand evidence.

Overall product completion estimate **~49% unchanged**, because the core actual URL → owner API/DB → functional generated application is still unproven.
