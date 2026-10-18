# Nail Atlas — Independent AI review pack

Scope: independent FastAPI/SQLite/Javascript dashboard built from public screenshot/user-operated flow observation; no source extraction or live integration. Original `/shop` and `/jobs` unaffected.

Core code: `db.py` (fictional seed + schema), `repository.py` (data adapter), `metrics.py` (calculation), `app.py` (API) and `static/app.js`/`style.css` (UI). API is read-only, example reports 208 fictional posts and 30 tag labels. Product flows: dashboard brand filter, category filter, all-brand compare, top-20 pagination and reset on brand change.

Priority review: `metrics.tag_summary`, `metrics.dashboard`, `metrics.top_posts`, `app.create_app`, `static/app.js` `chooseBrand`/`render`; inspect actual test traces in `TEST-REPORT.md`. Cross-check backend aggregation with raw SQLite. Check XSS, untrusted inputs, db-file handling and URL state.

Known limitations: original demand/performance index formulas unknown, demo formulas labelled; individual performance score intentionally null; static fictional report only; no user DB/API connection, no authentication (public dummy-only app), no actual posts or links. Browser automation within ChatGPT sandbox may be administrator blocked (see TEST-REPORT). Screenshots from original are not copied, logos/images are not copied.

Production work required: authentication/authorization, DB migration/backup, data-source adapter and schema mapping, ingestion validation and retry/dedup, report snapshots, actual metric definitions approved by domain owner, pagination at SQL layer, monitoring, deployment, scale tests and browser E2E from supported machine.
\n## Regression verification 2026-10-18 18:17 KST

New SQL-to-API cross-checks and edge tests are appended to tests/test_dashboard.py. Actual execution: pytest 33/33 PASS, two-process Uvicorn restart and unchanged SQLite DB PASS, Python/JS syntax PASS. One defect fixed: denominator zero incorrectly displayed 0%; now returns null and renders a dash. Production browser automation remains unverified; no claim of source index formula recovery or customer DB/API integration.

