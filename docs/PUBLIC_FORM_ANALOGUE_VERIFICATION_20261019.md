# ASTRA p4 — public-documentation functional analogue verification, 2026-10-19 KST

## Implemented, tested and uploaded

Four tested source files on isolated branch, functional commit `1631ab69e3a1fda4629a8ada76a53e184d8c67b9`:
- `astra_contracts/public_form_analogue.py`: SHA-pinned documentation → independently generated fixed FastAPI form
- `scripts/build_public_form_analogue.py`: dry-run by default, explicit `--generate` into fresh system-temp child
- `tests/test_public_form_analogue.py`: 23 new tests
- `docs/PUBLIC_DOCUMENTED_FORM_ANALOGUE_V01.md`: documentation, exact limitations, reproduction steps

All four Git blobs were independently fetched, SHA-1 compared to local tested files, and matched exactly:
`82670b1e797d2473fe7c3262f8e28b282afd13c5`,
`2bb9601a864e6e4e0124c2b16619a4d99bea2585`,
`9bc527cbcfd015ae884a428ed6999fcd34a6a809`,
`c12c218fda93ed41b8bea1f20de96550dd27768e`.

## What is genuinely verified

- Public **read-only** third-party web result for Selenium's form shows text input and Submit. Official Selenium documentation describes the `my-text` field, clicking Submit, and checking `Received!`; independently retrieved publisher output page `https://www.selenium.dev/selenium/web/submitted-form.html` shows `Form submitted` and `Received!`. The query-parameterized page was inaccessible via the read-only web tool.
- A **direct container HTTPS GET** to `https://www.selenium.dev/selenium/web/web-form.html` failed DNS resolution (`NameResolutionError`) during this turn. No retry and no blocked-browser workaround.
- Generated local FastAPI app uses **its own** `POST /submit` design to demonstrate the documented user-facing mechanic: input → Submit → HTML result `Received!`. This does not claim the original website's HTTP method/URL or source code.
- **23/23 new automated tests PASS**, including generated app `GET /`, form submission, fake input validation, output provenance, paths, and evidence/authorization guard. `compileall -q astra_contracts scripts tests` PASS.
- **Actual local Uvicorn HTTP: 8/8 PASS**: `GET /health` 200, `GET /` 200, two valid submits 200, bad/missing input 422, wrong media type 415, oversized request 413.
- A complete `pytest --collect-only` saw **739 tests** (716 previous baseline +23 new). Across disjoint rerun partitions **665/739 cases PASS**: 355 core/public tests (including 23 new) +203 acceptance/core+40 schema reuse+17 CRUD embed+24 query embed+25 DOM/review. The remaining 74 long-running generated UI test cases (23 query UI +20 mapping UI +31 transition UI) were **NOT rerun to completion**: one grouped run and a subsequent single-file query UI run hit tool timeout; further repeats were stopped. **Do not claim 739/739 PASS**. The previous 716/716 is an earlier-turn baseline, not this turn's full-suite result.

## Evidence, permission and product limits

`original_site_click_executed=false`; `original_site_submission_executed=false`; `original_site_behavior_verified=false`; `original_site_http_method_verified=false`; `source_code_copied=false`; `customer_db_or_api_connected=false`; `deployment_authorized=false`; `ui_mapping_approved=false`.
`GenerationContract` remains `blocked_pending_review`.
The project still cannot accept an arbitrary URL and produce a customer-data-backed production app without substantial further engineering. The existing `main` (SHA `dc23ee604d02513c890615a3a98440c1ea8a5270`) and customer data were not changed; no GitHub Actions used.

## Output and next bounded task

Local generated-artifact ZIP: `astra_p4_public_form_analogue_demo_20261019.zip`; local HTTP report: `astra_p4_public_form_local_http_20261019.json`; verification manifest: `astra_p4_public_analogue_verification_20261019.json`.
Run `python -m scripts.build_public_form_analogue` for dry-run; `python -m scripts.build_public_form_analogue --generate` to write a new temp demo; run generated `app:app` on `127.0.0.1` only.

Next `ㄱ`: if a genuinely available authorized browser surface exists, perform exactly one public form click and capture firsthand before/after evidence (stop on block); otherwise extend the **explicit documented-control-to-independent-app contract** to another small, grounded form widget or user-owned schema interface. Avoid repeating blocked browser or slow UI suite loops. Progress estimate conservatively ~49% unchanged because the real reference site's interaction and generalized original-URL→app equivalence are not proven.
