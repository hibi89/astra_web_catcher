# ASTRA p4 — Explicit fictional-column sorting and typed equality filtering v0.1

## Scope and safety

A reusable read-only FastAPI query adapter runs against **two different, explicitly declared synthetic physical schemas** without guessing column names. This unit does not change the older generated demo's `app/main.py`, change an owner database, compose arbitrary SQL, or grant implementation/deployment permissions. The new query route lives in `astra_contracts/schema_query_extension.py` and is exercised separately in memory or via loopback Uvicorn. A later step must integrate it with generated project output; this module by itself is **not** a generic production generator.

Inputs are `AlternateSyntheticTable` fixtures from the preceding schema-reuse unit: products `sku, display_name, family, popularity` and support tickets `ticket_key, summary, lane, priority`. Every physical column must be explicitly mapped to one of four known logical fields (`id`, `title`, `category`, `score`). Additional physical fields and live sources are rejected by the previous model.

The new GET `/api/rows` route requires `sort_by` to match a declared **physical** column exactly; `direction` is `asc` or `desc`; optional paired `filter_by` and `filter_value` implement exact equality, case sensitive for string values. The `score` column's filter parses only canonical nonnegative integer text between 0 and 10000, rejecting floats, signs, padded numbers, booleans, expressions and SQL-like strings. `limit` is 1–100. Stable ties preserve ascending synthetic IDs even under descending score order. All output returns only declared fictional physical rows, with explicit `synthetic` and false original-behavior flags. Unknown fields, invalid types and illegal parameters return HTTP 422. No database queries or write endpoints exist.

## Reproducible local verification

```sh
python -m astra_contracts.schema_query_extension fixtures/synthetic_reuse_products_table_20261019.json fixtures/synthetic_reuse_products_query_cases_20261019.json
python -m astra_contracts.schema_query_extension fixtures/synthetic_reuse_tickets_table_20261019.json fixtures/synthetic_reuse_tickets_query_cases_20261019.json
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

One API query is `GET /api/rows?sort_by=priority&direction=desc&filter_by=lane&filter_value=Open` on the fictional tickets app, returning payment (95) then the two 45-score tickets in ID order. This is fixture-only behavior, never evidence of an observed third-party website. To run locally, load a **synthetic table** into `AlternateSyntheticTable` and pass `create_query_app(table)` into `uvicorn.run(...,host='127.0.0.1',port=...)`; do not expose this unauthenticated demo to a public network.

## Acceptance contract

Each separately authored `QueryPlan` is SHA-256-bound to the exact source table and contains expected physical-field sort/filter/query result IDs. The verifier runs real FastAPI TestClient requests, checks HTTP status 200, complete physical columns, exact returned rows and result ID ordering. It rejects stale table hashes, forged permission fields, duplicate case IDs, invalid sort fields/expected results and missing filter/sort coverage. A hash checks consistency, not data ownership or human consent.

## Verified result (local, 2026-10-19 KST)

- Products: **9/9** query scenarios PASS.
- Support tickets: **9/9** query scenarios PASS.
- Newly added tests **30/30 PASS**, full pytest regression **477/477 PASS** (previous 447), Python compileall PASS. One pre-existing unrelated `httpx` deprecation warning.
- No GitHub Actions, blocked Chromium retrial, customer DB/API, production deployment, original-site functionality validation or feature promotion.

**Next bounded unit:** Connect this optional read-only query router with a generated isolated synthetic app so that generated artifacts themselves expose sorted and typed-filtered routes, with per-fixture regression tests. Keep `GenerationContract=blocked_pending_review` for any customer-backed code generation.
