# P4 ASTRA — disposable SQLite to API to Chart/Table integration

Date: 2026-10-19 KST
Scope: one bounded synthetic-only integration unit; protected main unchanged.

## Goal, boundary and design

Link the existing review-only chart/table preview to an actual read-only HTTP API with a genuine SQLite backend, while **never connecting to a user/customer database or granting generation/deployment approval**. This validates the mechanics of fetching data and presenting it, not OWID metric semantics or the general URL-to-app product.

There were two possible approaches:
- Mocked arrays or local JSON served to a browser: faster but does not prove a database query or backend API.
- Private in-memory SQLite plus a minimal FastAPI factory and reuse of the existing chart/table renderer: selected. An SQLite :memory: database holds strictly validated *invented* rows; GET /api/demo/series queries the SQLite snapshot and returns JSON; GET /preview queries the same store and produces real chart/table HTML. The browser additionally issues fetch('/api/demo/series') and checks the canonical SHA-256 of the record snapshot and the record count against its HTML. A stale or mismatched response does **not** claim a valid connection.

This is server-rendered HTML backed by SQLite, with a separate read-only API checked by frontend JavaScript. It is **not** an independent client-rendered SPA or a live/push-update UI; refreshing the preview is required to reflect a new SQLite snapshot.

## Code and interfaces

- astra_contracts/synthetic_sqlite_dashboard.py — SyntheticMemoryStore and create_synthetic_app factory. Uses a private sqlite3 :memory: connection, fixed SQL with parameter binding, a composite entity/time key, transactional replacement for the *in-process local test driver only*, a thread lock, and lifespan cleanup that destroys the DB.
- tests/test_synthetic_sqlite_dashboard.py — 13 pytest checks covering API GET and no mutation routes, 15 actual SQLite rows and chart points, proper provenance/headers, the API and HTML changing together after a synthetic-only server-side update, transactional invalid-row rejection, independent memory stores, owner-declaration rejection, five malformed cases, SQL-injection-like strings as plain data, and escaped HTML payloads.
- scripts/p4_synthetic_sqlite_browser_smoke.py — starts a temporary Uvicorn server **bound only to 127.0.0.1**, drives actual Chromium through HTTP, verifies browser-initiated GET /preview and fetch('/api/demo/series'), chart/table button + Enter/Space, updates one in-memory data value from 18.5 to 666.125 and reloads, and deliberately supplies a forged same-count API response with a different SHA to verify the UI marks its API link as unverified. No other network origin is permitted.
- .github/workflows/p4-synthetic-sqlite-integration.yml — scoped automated API contract and real-browser E2E jobs; no database secrets, production system, archive download, or external website queries. Existing requirements.txt already provides FastAPI/Uvicorn/pytest/Playwright; no new runtime dependency.

Only two GET endpoints exist:
- GET /api/demo/series — synthetic fixture metadata, 15 in-memory rows, SHA256, unapproved binding declaration and blocked generation contract.
- GET /preview — HTML produced from the same read-only SQLite snapshot and a local API readout; no POST/PATCH/DELETE route.

## Executed evidence (do not inflate)

**GitHub Actions [run 39222673267](https://github.com/hibi89/astra_web_catcher/actions/runs/39222673267) at exact feature commit 6e684c0153f5355a0a5ca1a08b05df3122b8503f: completed / SUCCESS; both jobs succeeded.**

- Ubuntu, Python 3.13: 13/13 synthetic SQLite FastAPI contract tests **PASS** (1 warning) from the actual repository checkout; Python compileall PASS.
- Ubuntu headless Chromium 156.0.8078.4: actual **127.0.0.1 HTTP → FastAPI → in-memory SQLite → HTML/API** browser E2E **PASS**. Browser did fetch the API; display updated after an in-process fake data update and reload; forged API snapshot rejected; Chart↔Table/keyboard succeeded. External-origin requests 0, JavaScript errors 0. Result artifact [12172815105](https://github.com/hibi89/astra_web_catcher/actions/runs/39222673267/artifacts/12172815105).
- Local Python 3.13.5 selected suite including previous observation/mapping/preview tests: 63/63 PASS against a locally prepared, corresponding code snapshot. The two source files relevant to the new demo are additionally verified by the GitHub Actions checkout and its results.

A first local Chromium page.goto to localhost was blocked with ERR_BLOCKED_BY_ADMINISTRATOR. The browser-localhost result is therefore **claimed only from the later successful GitHub-runner E2E**, not from the restricted local browser. API-level local TestClient passed; no host protections were bypassed.

## Reproduction

From a clean checkout of the feature branch, install packages already declared by the repository:

    python -m pip install -r requirements.txt
    python -m pytest -q -ra tests/test_synthetic_sqlite_dashboard.py
    python -m playwright install --with-deps chromium
    python -m scripts.p4_synthetic_sqlite_browser_smoke --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json

This script runs its own temporary loopback HTTP server, closes the browser, shuts down the server and disposes of its SQLite :memory: database. No user action is required for reproducing the confirmed GitHub CI run.

## Not approved and not proven

- **Owner schema/DB/API integration: NONE.** Data is 15 fabricated nail trend measurements with a made-up index and unknown business semantics. No OWID calculation correctness, behavior parity, real-world data mapping, input governance or customer credential was tested.
- No public hosting, production URL, permanent SQLite DB file, migration, external service API, or deployment is created.
- CSP currently allows inline script/style because the inherited standalone demo uses inline code; this is not production-hardening or a comprehensive penetration test.
- Evidence ZIP provenance verification remains separate. There is no assertion that the old OWID ZIP was revalidated by this new run.
- Read-only HTTP routes are suitable only for explicitly synthetic data. Owner-backed authentication, access control, rate limiting, schema reconciliation and explicit semantic approval would be needed before integrating real data.
- All approval flags remain false, and generation_contract is blocked_pending_review.

A conservative subjective roadmap estimate may move from ~49% to **~50%** for this bounded synthetic integration milestone; this is not a measured test percentage or a statement that the end product is half commercially ready.

**Next bounded unit:** add disposable owner-like schema mapping and negative owner-data isolation tests, or design a real-data integration handoff subject to explicit user/owner approval. Do not merge protected main or contact customer DB without authorization.
