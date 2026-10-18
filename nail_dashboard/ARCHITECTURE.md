# Nail Atlas Architecture

`schema.sql` → `db.py` (idempotent sample seed) → `repository.py` (SQLite SELECT adapter) → `metrics.py` (pure aggregates and explicit demo formulas) → `app.py` (validated read-only FastAPI handlers) → `static/app.js` and `static/style.css` (4 views).

API endpoints: `GET /nails`, `GET /nails/health`, `/api/nails/reports/latest`, `/api/nails/brands`, `/api/nails/overview?brand=`, `/api/nails/tags?category=&page=&per_page=`, `/api/nails/brands/compare`, `/api/nails/posts?brand=&page=&per_page=`. Swagger under `/nails/api-docs`.

ReportRun 1:N Post; Brand 1:N Post; Post N:M Tag through PostTag. `analyzed` is stored per Post. Reactions, counts, weeks, median, averages, tags, and rank are computed on request. `views` nullable and `performance_index` intentionally null: unknown source formula. `brand.four_week_index` and `tag.demand_index` are calculated using clearly defined demo-only formulas. No live source API calls and no static hardcoded result arrays in JS.

Top 20 order = `reactions DESC, id DESC`, then page 15. Brand changes in the client set `state.page=1` and fetch new `/api/nails/posts`; query parameters + fragment preserve state across reload/back. Category changes reset `state.tagPage=1`. The brand comparison endpoint returns all four rows independently of selection. Tags aggregate across all brands as observed, while the currently selected brand remains in the sidebar. Filter meaning is explicit to avoid implying the original website's hidden logic.

All endpoints read only. No identity/authentication in this standalone **public fictional demonstration** because there are no user accounts or private records. SQLite file lives outside Git versioning; local file must remain private to operator. FastAPI Query/Pydantic validation rejects invalid page or tag category, and brand lookup rejects unknown selection. HTML is escaped and no raw site assets or Instagram URLs are seeded. The recent-run refresh button calls the local report read endpoint only, with no n8n calls.

User DB/API future integration: replace `repository` read adapter while keeping typed response shape & `metrics` pure functions; add validated ingestion and report-run snapshots; enforce per-tenant access and rate limits before exposing real customer data. The original data model, Instagram private API, and indexing criteria are unknown.
