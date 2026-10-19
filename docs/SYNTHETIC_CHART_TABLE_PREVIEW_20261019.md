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
