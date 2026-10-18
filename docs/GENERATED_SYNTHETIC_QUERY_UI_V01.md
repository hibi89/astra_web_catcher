# ASTRA p4 — Generated synthetic sort/filter UI v0.1

## Delivered functionality

`astra_contracts.schema_query_ui.embed_query_ui(root)` augments an **existing, verified, disposable generated synthetic preview**, after the read-only query adapter and opt-in synthetic CRUD modules have passed their earlier acceptance contracts.

It adds only these files, without modifying the original generated templates:

- `app/ui.py`: optional **localhost-only** `app.ui:app` entrypoint with `GET /preview` and `GET /api/preview-schema`.
- `app/query_ui.html`: Korean-language visible controls for choosing a declared physical sort field, ascending/descending direction, optional exact-match text/integer filter, and query submission. Results appear in an HTML table.
- `tests/test_embedded_ui.py`: independently executed generated-project acceptance of the actual combined FastAPI app.
- `README_UI.md` and `data/query_ui_embed_report.json`: usage and contract.

The page fetches field names/types exclusively from the explicit synthetic schema at `/api/preview-schema`; it uses `URLSearchParams` for read-only `/api/rows` requests and `textContent`/DOM creation for rendering data instead of injecting arbitrary HTML. The physical `score` mapping becomes a restricted integer input (0–10000). A missing filter value shows a validation message rather than submitting an ambiguous query. The original `/` route is preserved: `/preview` is a separate page.

## Verification and boundaries

- Existing source file guards require known byte-for-byte `app/main.py`, `app/index.html`, `app/extended.py`, `app/full.py`, `app/sandbox_crud.py`, earlier query fixture, and consistent approval-negative reports.
- Installation is limited to already existing `astra-synth-*` direct system-temp directories and rejects any previously existing/symlinked extension file before modifying output.
- Runtime verifies the fixed `app/query_ui.html` SHA-256 and already-existing physical fixture SHA. HTTP response headers disable UI caching.
- The generated UI entrypoint keeps synthetic CRUD **off by default**. Only `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY` enables the old fictional-only `/sandbox` CRUD mount, which is **not** exposed as an editor in this UI. Do not deploy or expose the unauthenticated test CRUD endpoint.
- Source-site behavior, owner/customer database, credentials, general schema inference, business logic inference, universal frontend reconstruction, and deployment authorization are **not** implemented or verified. `GenerationContract` remains `blocked_pending_review`.

### Test evidence

- Tests across two independent fictional physical schemas: `sku/display_name/family/popularity` (products) and `ticket_key/summary/lane/priority` (tickets).
- Generated-project FastAPI TestClient checks the page, schema, query acceptance cases, preserved original routes, and denied unauthorized original mutations.
- Real **localhost HTTP** checks using Uvicorn/httpx returned 200 for `/preview`, `/api/preview-schema`, and approved sort/filter operations; 422 for invalid fields; 405 for original unsafe writes; 404 for sandbox routes when off.
- UI JavaScript parsed and executed through a **Node.js DOM simulator**, verifying sort changes, exact text filter, integer input adaptation, and typed-filter result count in both schema variants.
- A browser attempt was blocked by administrator policy (`net::ERR_BLOCKED_BY_ADMINISTRATOR`) at `127.0.0.1`; **no actual browser page navigation, click-through, or screenshot is claimed**. Do not retry the blocked route in this execution environment. Browser compatibility requires independent human/browser test elsewhere.

## Local running

```sh
python -m uvicorn app.ui:app --host 127.0.0.1 --port 8017
```

Open `http://127.0.0.1:8017/preview` on the same machine. Never expose this demo to other hosts or real customer data.

**Next bounded step:** Verify the generated UI manually in the user's authorized local browser or improve the accepted observed-feature-to-independent-UI mapping contract; no automatic production import.
