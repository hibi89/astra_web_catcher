# ASTRA p4 — second real website observation: OWID chart → data table

**2026-10-19 15:42 KST · verified public reference · no customer data**

## Source selection and reason

The older user-linked Japanese nail dashboard reference `https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/` was not reachable through the current public web retrieval surface. Do not assert that this original dashboard was re-tested. Instead, to exercise a **different public real-world dashboard mechanism** rather than repeating Selenium's form toy example, selected <https://ourworldindata.org/grapher/life-expectancy?tab=chart>, a public, published statistical chart and country table. The publisher labels the content CC BY (attribution required). No authentication, customer records, private API or other third-party data extraction was attempted.

## Real browser action (independent of simulated tests)

- GitHub Actions [run 39211418515](https://github.com/hibi89/astra_web_catcher/actions/runs/39211418515): **completed / success**; original repository checked out by GitHub runner Python 3.13.16 and Chrome/Xvfb.
- Runner executed **43/43 offline tests PASS** (12 new synthetic dashboard tests + 5 one-shot existing intake tests + 5 existing capture-chain tests + 21 Selenium fake tests). These prove the internal contract, **not** source-site clicking by themselves.
- The real Chrome runner then visited source URL, found the **visible Table control**, clicked that actual UI control (not a JavaScript forced state change), and waited for visible table rows.
- Real browser changed **0 visible DOM table-body rows before** to **265 DOM rows after**. Screenshot evidence visually inspected: line chart with region series before; country/region tabular data after, including the table's `Country or region`, `1543`, `2023`, interval, absolute-change and relative-change columns. No country-filter calculations or source formulas independently verified.
- Runner logged `PUBLIC_DATA_DASHBOARD_TABLE_ACTION_REPORTED; SCREENSHOTS_2_OF_2_HASH_MATCH; HUMAN_REVIEW_PENDING`, then uploaded exactly six files as artifact.

## Genuine screenshot evidence review

Artifact `p4-owid-chart-table-screenshots` (GitHub ID **12168150702**), [GitHub artifact](https://github.com/hibi89/astra_web_catcher/actions/runs/39211418515/artifacts/12168150702), 274126-byte ZIP. Exact downloaded ZIP SHA-256:

`6ad5f561b78271be7da3b4efb8e61fcc1a6c269b4ebf8a26e1b32c23b81717e6`

This **matches GitHub's own uploaded artifact digest**. Artifact expires 2026-10-22 06:42:29 UTC / 15:42:29 KST.

Actual ZIP files, independently opened:
- `captures/before.png`: **159304 bytes**, 1050×861 RGB; visually shows life-expectancy line chart.
- `captures/after.png`: **122367 bytes**, 1050×861 RGB; visually shows life-expectancy table with filter and a cookie banner. Screenshot not identical to before.
- `bundle.json`: original ASTRA `ObservationBundle`, `certainty=inferred`, `before.visible_table_rows=0`, `after.visible_table_rows=265`.
- `request.json`: original `CaptureIntakeRequest` with two real screen captures.
- `intake_manifest.json`: original `CaptureIntakeManifest` (2/2 file SHA and byte lengths).
- `result.json`: runner's status and nonapproval flags.

**29/29 independently executed local checks PASS** on downloaded ZIP, parsing the actual Pydantic models from the project, computing canonical SHA fingerprints for bundle/request/manifest, comparing both PNG SHA-256/size/ref links, confirming monotonic timestamps (2026-10-19 06:42:28.513725 to 06:42:29.202048 UTC), verifying PNG headers and actual image differences, verifying 0→265 reported rows, and checking false approval flags. This confirms artifact integrity and an actual visible UI transition with GitHub runner evidence, **not the underlying source data lineage or authorized mappings**.

## Mechanism skill and owned-schema gap analysis

**Observed mechanism** (supported by actual Chrome before/after images and DOM count):
- A public chart has mutually exclusive visual modes (Line and Table). Pressing Table replaces plotted time series with a scrollable, sortable table of country/region records; the date-range control remains.
- Table view shows the same subject matter through a different UI representation. The site may have client code/backend/data APIs, but which exact internal implementation produced the state switch **was not verified**.
- The six visible headings are presentation-level field labels; `1543 to 2023` and relative-change values do **not** prove a particular aggregation or calculation formula. Mark such formulas **unknown**, not discovered.

**Owner data mapping**: the only user-owned schema snapshot available to this ASTRA feature branch is the **fictional application DDL** (`categories`, `products`, `companies`, `job_postings`). None represents `country,year,life_expectancy` or time-series country metrics. Therefore:
- **0 approved semantic field bindings** for the OWID chart.
- **Missing resource**, **missing time-series observation entities**, and **unverified year/value formulas** are explicit blockers. Do not repurpose `products.stock` or `job_postings.region` as life expectancy merely because a name seems similar.
- The publisher's public CSV/metadata is a *reference dataset*, **not** the user's authorized existing DB. To implement this feature with *the user's* data, obtain a read-only schema declaration showing entity IDs, dates, numeric measure, optional country/category, and aggregation semantics; map only after user review, then test on a **disposable owned DB**.
- The UI skill is reusable as a proposed **chart/table mode switch**, but no general generator, production app, owner DB/API or authentication integration was created or approved.

## Dev changes, tests and protected assets

Files added on feature branch:
- `scripts/public_owid_dashboard_probe.py` — explicit `--run`, public single-domain/path allowlist, redacted screenshot intake, safe default dry-run.
- `tests/test_public_owid_dashboard_probe.py` — 12 fake-driver and fail-closed cases.
- `.github/workflows/p4-public-owid-dashboard.yml` — feature-only live public dashboard action, read-only contents token, 8-min timeout, 3-day evidence retention.

For observable PR-triggered run, temporarily forked `ci/p4-owid-observation-20261019` and changed **only** workflow PR event on that one-commit verification branch; created [Draft PR #2](https://github.com/hibi89/astra_web_catcher/pull/2) with base `feature/observation-contract-20261018`, NOT `main`; after verified success, **closed it without merging**. Protected `main`, original DB and test user data unchanged; no Vercel deployment.

**What remains unverified:** site-specific adaptation to the original Japanese nail project, actual filter/sort/CRUD beyond chart→table, automatic function inference for arbitrary URLs, existing owned DB/API integration, field semantics, full historical 739+ tests, independent permission review and production readiness. `GenerationContract=blocked_pending_review`; overall conservative roadmap estimate **~49%** despite one new meaningful original-site mechanism pass.

**Next bounded unit:** implement **review-only** chart/table state-transition contract as a reusable mechanism skill using *actual* pinned observation evidence IDs; never equate this with data mapping approval. Or, when the user supplies a sanitized, genuinely owned schema and target reference, prioritize the full small-slice UI→owned disposable DB flow.
