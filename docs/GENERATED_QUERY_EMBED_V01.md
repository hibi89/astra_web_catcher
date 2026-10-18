# ASTRA p4 — Query API inside the generated synthetic web app (v0.1)

## What changed

The prior `schema_query_extension.py` ran an **independent** read-only FastAPI app for explicit fictional physical columns. This unit adds `schema_query_embed.py`, which packages an equivalent **read-only `/api/rows` endpoint into the already generated synthetic FastAPI project itself**. It creates an **optional** entrypoint `app.extended:app`, loading the same existing `app.main.create_app`, with the same `/`, `/health`, `/api/items`, `/api/items/{id}` routes plus `/api/rows`. The original `app/main.py`, HTML, fixture seed and all protected templates are not edited. Launching with the old `app.main:app` still serves the original demo; launching `app.extended:app` enables the extra query route.

No source-site code, real DB, credentials, URL fetching, user file migrations or unapproved app generation occurs. The inputs must be `AlternateSyntheticTable` (exact four explicitly bound physical columns), `QueryPlan` (SHA-bound expected IDs) and the existing isolated preview. All schema approvals and real-site verification remain false.

## Single-command synthetic pipeline

From repository root, using a **new caller-created empty directory directly below the OS temporary folder** whose name begins with `astra-synth-`:

```sh
OUT=$(mktemp -d /tmp/astra-synth-XXXXXXXX)
python -m astra_contracts.schema_query_embed \
  fixtures/synthetic_manual_filter_observation_20261019.json \
  fixtures \
  fixtures/synthetic_manual_filter_schema_20261019.json \
  fixtures/synthetic_generation_request_20261018.json \
  fixtures/synthetic_reuse_products_table_20261019.json \
  fixtures/synthetic_reuse_products_cases_20261019.json \
  fixtures/synthetic_reuse_products_query_cases_20261019.json \
  "$OUT"
cd "$OUT"
python -m pytest -q tests/test_app.py tests/test_embedded_query.py
python -m uvicorn app.extended:app --host 127.0.0.1 --port 8017
```

Second fictional table: replace `products` with `tickets` in the three fixture paths. The wrapper verifies expected query IDs and SHA **before writing any file**, runs the already implemented and blocked source→synthetic preview pipeline, checks fixed templates, then embeds the optional route and **executes the packaged generated project's own tests in a separate Python interpreter**.

## Generated artifacts

New files in the isolated project: `app/extended.py` (fixed, self-contained FastAPI route template with expected SHA of the synthetic physical table), `data/query_physical_fixture.json` (explicit fictional rows), `data/query_cases.json` (independently authored acceptance expectations, never evaluated as executable code), `tests/test_embedded_query.py`, `README_EXTENDED.md` and `data/query_embed_report.json` (only after self-tests pass). Baseline `app/main.py` and `app/index.html` remain byte-for-byte unchanged. The physical rows are in memory for query operations and do not touch the baseline SQLite database; `app.main` retains its own throwaway synthetic SQLite fixture.

`/api/rows` supports: `sort_by` an explicitly bound column; `direction=asc|desc`; paired `filter_by`/`filter_value` for **case-sensitive exact match** of text or strict nonnegative canonical integer up to 10000; `limit` 1–100; deterministic ascending ID tie-breaks. Unknown columns/directions, unsupported numeric values and missing pairs return HTTP 422; mutation verbs return 405. The generated app is intentionally free of the `astra_contracts` package import, so it runs from the isolated generated folder with declared requirements only.

The extension checks an SHA-256 embedded in trusted generated Python code against the bundled physical JSON every time the app loads. A changed JSON file or a symlinked JSON fixture blocks launch. This is **self-consistency**, not trusted-origin authentication: someone who can rewrite executable Python can remove the check. Likewise, user-authored query expected IDs are acceptance examples, not proof of an original website's business logic.

## Safety, validation and limitations

- Validate `QueryPlan.source_table_sha256`, all typed rows, independent expected IDs, existing generated preview source bytes and `blocked_pending_review` trace before modifying the new output folder. Reject overwrites, symlinks, destinations outside the direct system temp folder and forged permissions. Existing source site and schemas are not touched.
- The extended entrypoint calls the original `create_app()` and shares its *generated* routes. It does not change the default original `app.main:app` process. No CRUD, generic code generation, arbitrary schema discovery, customer DB/API integration, original-site formula reproduction, browser GUI E2E or production deployment.
- Tests: full regression `python -m pytest -q tests/test_*.py`; generated tests for product/ticket samples; real local `uvicorn app.extended:app` + `/health`, `/api/items`, `/api/rows` valid/invalid HTTP requests. The original protected generator remains byte-identical.
- The checked, fixed read-only query endpoint and a generated self-contained entrypoint are actual running code, **but only for deliberately fictional four-field fixtures**. The production preflight still blocks real independent code generation; all permission flags in the report remain false.

## Next milestone

Introduce independently specified and accepted **CRUD flows on a disposable synthetic DB** before any owner-data operations, or demonstrate the first permitted real-world source with actual captured behavior and separate human approval. A real URL→owned DB→functional app remains outstanding.
