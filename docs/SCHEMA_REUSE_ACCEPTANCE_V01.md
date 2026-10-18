# ASTRA p4 — Explicit multi-schema acceptance reuse v0.1

## Delivered scope

A single CLI receives a **fictional** table with a fully explicit four-column mapping, normalizes its rows into the existing fixed `SyntheticDemo` contract (`id`, `title`, `category`, `score`), runs the earlier operator-reported one-event pipeline, then runs the **same feature acceptance adapter** over an entirely new isolated FastAPI+SQLite instance. This is a genuine end-to-end reuse test across different *physical field names*, not a different collection of rows in the same source schema.

Verified test fixtures:

| Fixture | Physical fields → logical fields | Rows | Explicit functional acceptance checks |
| --- | --- | ---: | ---: |
| Fictional product catalog | `sku → id`, `display_name → title`, `family → category`, `popularity → score` | 3 | 6 |
| Fictional support tickets | `ticket_key → id`, `summary → title`, `lane → category`, `priority → score` | 4 | 7 |

Both reuse the same filter/list/search/detail test machinery, with exact **operator-supplied** expected IDs and ordering. Scenarios include limits, tie ordering, literal `%` and `_` escaping, case-insensitive search, existing/missing detail (200/404). Only *one* filter scenario per table illustrates the unrelated original reported source observation; other tests are explicitly labelled independent fixture checks.

**Critical boundary:** this is not automatic customer schema discovery, arbitrary table querying, raw DB connection, real application code generation, replay of a reference website, or evidence that an original click worked. Both tables and all rows are invented. The mapping is explicit and only normalizes four known attributes into a **fixed code template**. Owner-supplied source kinds and production rights are rejected. The original site's formula/interaction, true source data, reviewer identity, consent, authorization and deployment remain unverified/false; `GenerationContract` stays `blocked_pending_review`.

## Exact contract

`AlternateSyntheticTable` validates `source_kind=synthetic_fixture`, `run_mode=temporary_demo_only`, precisely one binding for each of four logical fields, four distinct physical columns, strict row-key equality to those columns (no incidental PII/unknown-column passthrough), strict scalar types, <=100 rows, distinct IDs, and the underlying `SyntheticRow` limits. Arbitrary names are not SQL-interpolated. An extra/missing/duplicate binding or field, bad type, invalid name, duplicate row identifier, or claimed verification/authorization fails closed.

`SchemaAcceptanceCases` binds exact physical table hash, source-illustration label and explicit expected status/ordered IDs to the fixture. It rejects stale hashes, forged verification rights, missing or mismatched original source ID/feature, and incorrect expectations **before any output is generated**.

Only the existing caller-created empty `astra-synth-*` directory directly under the system temporary folder is writable. Existing UI, code, data and source claims are immutable. The canonical owned-schema declaration used by the earlier pipeline remains explicitly `synthetic_fixture`; it refers only to the **fictional demo interface**, not the incoming physical table or a user's real database.

Upon success the command creates the pre-existing nine synthetic files plus `data/schema_reuse_report.json` with digests, physical field names, row/case counts and all authority flags `false`. The adapter still verifies exact generated template bytes and uses disposable SQLite data during real HTTP/ASGI acceptance assertions. This report is descriptive trace metadata, not signed provenance.

## Reproduction

From repo root, install the existing Python test requirements and run either:

```bash
OUT=$(mktemp -d /tmp/astra-synth-reuse-products-XXXXXXXX)
python -m astra_contracts.schema_reuse_adapter \
  fixtures/synthetic_manual_filter_observation_20261019.json fixtures \
  fixtures/synthetic_manual_filter_schema_20261019.json \
  fixtures/synthetic_generation_request_20261018.json \
  fixtures/synthetic_reuse_products_table_20261019.json \
  fixtures/synthetic_reuse_products_cases_20261019.json "$OUT"
```

Or replace both `products` occurrences by `tickets` and create **a new empty** output folder.

```bash
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

## Verification and limitations (2026-10-19)

Full local pytest and standalone CLI executed on both fictional schemas. The original source observation and evidence remain *operator-claimed* data with no independent real-site interaction; generated code implements the same four logical fields in both cases. No GitHub Actions, blocked Chromium retry, real user DB, live site, original app change, new permission or production deployment.

### Next unit

Expand to one **additional supported logical feature** (e.g. optional validated field/value filter or safe sort) from explicit test assertions, or introduce a *reviewed, separately authorized* integration contract before any customer data. Do not equate physical schema-name reuse with production DB interoperability.
