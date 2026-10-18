# ASTRA p4 — optional CRUD inside the generated synthetic preview (v0.1)

## Implemented

1. The trusted **existing generator** first creates a fictional FastAPI+SQLite project with `app/main.py` and the generated, strictly read-only `app/extended.py` query endpoint.
2. `python -m astra_contracts.schema_crud_embed /absolute/temporary/astra-synth-...` checks that the existing project is a directly rooted, non-symlinked system-temporary ASTRA preview; verifies the immutable base template byte-for-byte, the fixed read-only extension code and its synthetic fixture hash, the acceptance-plan contract, and the query extension report (including the original base-preview fingerprint).
3. Only after validation, the tool **adds** `app/full.py`, `app/sandbox_crud.py`, `tests/test_embedded_crud.py`, `README_CRUD.md`, and `data/crud_embed_report.json`. Pre-existing outputs cause an error; no source overwrites.
4. `app/full:app` exposes previous `/`, `/health`, `/api/items`, `/api/items/{id}`, and `/api/rows` endpoints without changes. Mutations are disabled by default. Explicit `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY` mounts separate CRUD endpoints under `/sandbox/api/items`; they use an independent, fresh, temporary SQLite DB and never alter the preview's main SQLite file.
5. Generated-project self-tests perform HTTP 201 creation, 200 lookup/update, 204 deletion, 404 missing record, 409 duplicate, 422 invalid typed value, 405 original-base mutation rejection, and off-by-default 404. Both fictional source schemas (product and support tickets) are exercised. All tests are synthetic examples, **not actual website behavior**.

## Developer-only local commands

From an **existing generated** ASTRA temporary preview, with the ASTRA repo on Python's import path:

```bash
python -m astra_contracts.schema_crud_embed /tmp/astra-synth-EXAMPLE
cd /tmp/astra-synth-EXAMPLE
python -m pytest -q tests/test_app.py tests/test_embedded_query.py tests/test_embedded_crud.py
python -m uvicorn app.full:app --host 127.0.0.1 --port 8017
```

This default launch **does not** expose CRUD. In a separate disposable developer-only session:

```bash
ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY python -m uvicorn app.full:app --host 127.0.0.1 --port 8017
```

Windows PowerShell equivalent: `$env:ASTRA_ENABLE_SYNTHETIC_CRUD='YES_TEMP_ONLY'` in the terminal running Uvicorn; unset with `Remove-Item Env:ASTRA_ENABLE_SYNTHETIC_CRUD` afterwards.

## Boundaries and risks

- Development-only demonstration, unauthenticated. Do **not** deploy, expose on public interfaces, or use real data. This is not a production database connector, authorization system, dynamic website parser, general schema inference engine, or production CRUD system.
- CRUD is on a *different, independently allocated* SQLite database, not on the physical-field fixture or the base demo's SQLite. The write feature is not shown in the HTML page yet; HTTP/JSON only.
- Existing protected `app/main.py`/HTML and read-only extension remain unmodified. The original website, owner DB/API, credentials, real user permissions, and deployment are never accessed.
- The embedded source is fixed module code that is independently reviewed, not extracted code from a site. Generated sandbox data may remain on disk if the process terminates abruptly before temporary-directory cleanup.
- Parent `GenerationContract` continues to report `blocked_pending_review`; both original-site verification and real owner database authorization remain false.

## Next bounded task

Make a useful interactive GUI for the fictional preview's search/sort/detail, and only later add a clearly separated opt-in sandbox editor; gather actual **authorized** URL/browser traces and owner DB mappings before making any claims about production functionality.
