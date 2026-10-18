# ASTRA p4 — Evidence → declared fields → read-only synthetic UI mapping v0.1

## What this unit actually does

`astra_contracts/observed_ui_mapping.py` is a **read-only, offline review contract**, not a site analyzer, browser recorder, original-interface clone, permission controller, or general-purpose code generator. It connects:

1. `ObservationBundle` — an operator-recorded state change, its action, and an evidence ID;
2. `OwnedSchemaDeclaration` — a **fictional** and explicit mapping of the changed UI field to a declared response/table field;
3. `AlternateSyntheticTable` — a separate **fictional** schema with exactly four physical-to-logical field bindings; and
4. `UIActionMappingPlan` — a separately authored, hash-pinned link choosing a synthetic exact-match filter field.

The result is a deterministic review-only report with per-link reasons and, only when all gates pass, a **synthetic preview candidate** for the existing read-only `/api/rows` endpoint. **No generated UI is changed in this unit.** The candidate is not applied, executed against a real website, or approved for a customer database.

## Actual examples (2026-10-19)

| Illustration | Operator-reported synthetic UI transition | Explicit fictional source mapping | Separate preview query | Result |
|---|---|---|---|---|
| Products | `selected_category: ALL → colors` | `fictional_filter_summary.selector_value` | `/api/rows?sort_by=sku&filter_by=family&filter_value=colors` | Fictional products **2 rows** |
| Tickets | `selected_lane: ALL → Open` | `fictional_filter_summary.selector_value` | `/api/rows?sort_by=ticket_key&filter_by=lane&filter_value=Open` | Fictional tickets **3 rows** |
| Archived brand report | Historic brand dashboard screenshot *described in a secondary research note* | `dashboard_summary.brand_key` (made-up) | None | **blocked: `archived_secondary_only`**; no click trace, formula or direct behavior verification |

The first two observations are **fabricated local acceptance fixtures**. Their `certainty: observed` is the operator's claim within the data structure, **not independent evidence of a visited website**. Even a candidate that passes all gates has `semantics_approved=false`, `synthetic_illustration_only=true` and `evidence_quality=operator_reported_not_independently_verified`.

## Gate behavior

- Reject stale SHA-256 hashes of the observation, explicit declaration or synthetic table; reject mismatched, altered or missing local evidence bytes. The evidence root and every path component must be local, non-symlinked and contained. Limit each artifact to 1 MiB. **Byte integrity does not authenticate that the reported behavior happened**.
- `unknown`/`inferred` claims cannot produce a candidate; `archived_report`-only claims are blocked. A field without a changed before/after value, or without a recorded action, cannot drive a preview filter.
- Feature support is deliberately limited to `filter` with an explicitly requested `exact_match_filter`. Other operations, including create/update/delete and aggregate formula claims, remain unimplemented.
- Require exact observation→UI field→declared resource/field matches. Reuse `compare_mappings` for structural type/nullability checks, reporting rather than upgrading incompatible or unsupported claims.
- Require the preview physical field to belong to the exact declared four-column fictional table. Require strict string or integer type agreement and an **exact (case-sensitive) equality match** in fictional rows. No guessing, name similarity, numerical coercion, auto-correction, cross-source semantics or SQL construction.
- No source website fetches, cookies, customer credentials, real DB/APIs, schema migrations, app deploys, GitHub Actions or GUI/browser retries. No production claim or approval flag may be set to true. The existing `GenerationContract` stays `blocked_pending_review`.

## Reproducible commands

From the project root:

```bash
python -m pytest -q tests/test_observed_ui_mapping.py
python -m astra_contracts.observed_ui_mapping \
  fixtures/synthetic_ui_mapping_products_20261019_observation.json \
  fixtures/synthetic_ui_mapping_products_20261019_schema.json \
  fixtures/synthetic_reuse_products_table_20261019.json \
  fixtures/synthetic_ui_mapping_products_20261019_plan.json fixtures

python -m astra_contracts.observed_ui_mapping \
  fixtures/jp_nail_brand_filter_observation_20261018.json \
  fixtures/synthetic_owned_schema_mapping_20261018.json \
  fixtures/synthetic_reuse_products_table_20261019.json \
  fixtures/synthetic_ui_mapping_archive_blocked_plan_20261019.json .
```

Sample reports are stored under `fixtures/synthetic_ui_mapping_*_report_20261019.json` for comparison. The report and CLI write nothing by default; stdout emits JSON only. Tests separately exercise the existing FastAPI `/api/rows` on each fictional table, checking the reported match counts, with the API's `original_site_behavior_verified=false` marker intact.

## Next bounded unit

After this traceability contract is reviewed, consider consuming its **explicit, still-unapproved synthetic preview candidate** in a local UI control; do not silently turn an offline mapping into customer-code generation. For an actual external website, first obtain and inspect authorized first-hand click/visual evidence and a declared owner schema. A historical screenshot note does **not** satisfy that requirement.
