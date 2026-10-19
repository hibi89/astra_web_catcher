# p4 synthetic Chart/Table preview — 2026-10-19

## Purpose and boundaries

The new offline preview uses an original SVG chart, a static HTML table, and a fixed local button handler to show the same explicitly invented synthetic time-series rows in two modes. It is a presentation-mechanism demo, **not a copy of OWID data, code, formulas, APIs, assets or proprietary functionality**, and not an approved owner-data implementation.

The optional archive argument verifies the original pinned public OWID screenshot ZIP via the existing fail-closed bridge (run 39211418515, artifact 12168150702, SHA-256 6ad5f561b78271be7da3b4efb8e61fcc1a6c269b4ebf8a26e1b32c23b81717e6). Without a local archive, the preview says that source evidence was not supplied. Passing the pinned proof only verifies recorded evidence integrity, not the reference site's calculation semantics.

## Files

- astra_contracts/synthetic_chart_table_preview.py — safe schema and row validation, SVG and HTML construction, explicit new-file-only CLI
- tests/test_synthetic_chart_table_preview.py — 25 new test cases
- examples/p4_chart_table_synthetic_schema.json — explicit synthetic schema and four required semantic roles
- examples/p4_chart_table_synthetic_rows.json — 15 **fabricated** values for three design labels across five monthly periods
- docs/SYNTHETIC_CHART_TABLE_PREVIEW_20261019.md — this document

## Reproduce locally

Use Python 3.11+ from the repository root. The output is standalone HTML and makes no network/DB calls.

    python -m astra_contracts.synthetic_chart_table_preview --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --output preview.html

To require pinned proof verification, add the argument --archive /path/to/p4-owid-evidence.zip. The archive must be the genuine immutable GitHub Actions ZIP; a fabricated or altered ZIP fails. CLI output uses exclusive file creation and refuses to overwrite an existing path.

The renderer requires explicit, distinct entity/period/measure/aggregation field mappings and accepts only source_kind=synthetic_fixture. It rejects missing/incompatible columns, unknown or missing row fields, duplicate entity and period pairs, mixed metric labels, nonfinite numbers, booleans passed as numeric measures, invalid years/months, mixed period granularities, and oversized datasets. The maximum is 240 rows, 10 entities and 24 periods. All user-provided text is HTML-escaped. Chart lines break at missing periods. The HTML prominently labels the result synthetic and unapproved.

## Measured evidence

- Python 3.13.5, pytest 9.0.2; 50/50 selected tests passed, 0 skipped, from the exact tested local source (previous selected 25 plus preview-specific 25):
    
    python -m pytest -q tests/test_chart_table_transition_skill.py tests/test_synthetic_timeseries_review.py tests/test_chart_table_synthetic_bridge.py tests/test_synthetic_chart_table_preview.py

- Python compileall on astra_contracts and tests: PASS.
- CLI with the declared example files and original 274126-byte pinned ZIP: PASS. Generated HTML: 7778 bytes.
- Chromium headless local smoke test with Playwright page.set_content of the exact generated HTML: initially Chart visible and Table hidden; selecting Table hides Chart and reveals 15 table rows; selecting Chart restores Chart and hides Table. Both screenshot states were captured and visually inspected.
- Direct file-URL navigation in this execution environment was blocked by administrator; therefore **file-URL navigation is not claimed to pass**. page.set_content is the tested browser path.
- GitHub Actions, full repository (739+), Windows Edge, owner database, production and deployment are NOT RUN in this unit. The 50 tests are a targeted scope, not evidence of a full system.

## Security/authorization

Output is local HTML and does not query endpoints, import owner data or modify any schema. The field matches are only structurally compatible, never semantically approved. Original OWID implementation and formula correctness remain unknown. Owner database access, code generation for owner systems and deployment remain unauthorized. GenerationContract remains blocked_pending_review. This does not raise the estimated overall roadmap completion above ~49 percent.

Next recommended bounded unit: broader clean-environment regression and manual inspection of the standalone preview, without accessing or modifying a customer system.

## 2026-10-19 — Expanded offline regression + Chromium five-viewport compatibility

- Code under test: exact feature SHA-matched Python code/test sources, including chart/table verifier, synthetic mapping, evidence bridge and preview. Fixture blob hashes matched GitHub: schema 6332f6a0765210e95b28cca2fb830db737b07615, rows 6f1c69e39cf4e2a05101d3b3cdca6c19d71978eb.
- Local Python 3.13.5, pytest 9.0.2: `python -m pytest -q -ra tests/test_chart_table_transition_skill.py tests/test_synthetic_timeseries_review.py tests/test_chart_table_synthetic_bridge.py tests/test_synthetic_chart_table_preview.py` → **50 passed, 0 skipped**. `python -m compileall -q astra_contracts tests scripts` → **PASS**.
- Added reproducible `scripts/p4_synthetic_preview_browser_smoke.py`: uses exact pinned OWID ZIP, strictly synthetic example schema/rows, and Playwright `page.set_content` in Chromium 144.0.7559.96 (Debian); five actual viewport contexts 1366×768, 1280×720, 768×1024, 390×844 and 320×640 → **5/5 PASS**. On all 5: 15 SVG points, 15 table rows, click Chart→Table and keyboard Enter/Space toggle, pressed/hidden state correct, overflow-x auto, no page JS errors and zero network requests. One separate malicious HTML onerror payload remained escaped: **1/1 PASS**. No screenshot-visual-equivalence claim for this run.
- Exact tested browser script Git blob **3713fe3016e994147107d746c643e3f5d450d977**. Chromium sandbox not disabled. Invoke from repo root after installing Playwright Python and system Chromium:
```bash
python -m scripts.p4_synthetic_preview_browser_smoke --chromium /usr/bin/chromium --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --archive /absolute/path/to/p4-owid-evidence.zip
```
- **Not tested:** Windows Edge, macOS Safari/WebKit, Firefox, direct file:// navigation (previously blocked), customer DB/API, arbitrary reference websites, 739+ full repo suite, new GitHub Actions, production/deployment. Viewport changes within Chromium do not establish cross-engine compatibility.
- Approval flags remain false; `GenerationContract=blocked_pending_review`; code limited to synthetic sample. Overall approximate ASTRA progress **~49% unchanged**. Next bounded step: cross-engine Windows/Edge browser verification in an eligible runtime, or disposable full repository regression once a clean checkout becomes available. Do not require user to manually test unless no other permitted method.
