# ASTRA p4 — fixture-only feature acceptance adapter v0.1

## Purpose

This is the first **operator-declared acceptance contract → real generated API response** adapter, following the earlier one-command fictional manual action pipeline. It does not copy the original site or translate its captured text into app business logic. The operator explicitly writes expected **synthetic row IDs**; the adapter checks their expected order against an independent fixture oracle and then compares them to an actual FastAPI/SQLite endpoint response in a disposable test DB.

Supported v0.1 feature cases: `list` (optional limit 1–100), `search` (literal substring including `%`/`_`), `filter` (exact category), and `detail` (existing 200 or missing 404). Create/update/delete, formulas, original styles, real auth, and DB adapters are **not** in this stage. The generated app remains the existing fixed synthetic FastAPI template, not dynamic source-code generation.

Each case is marked **either** `source_feature_illustration` with the **single exact** manual observation ID and the same feature type, **or** `independent_synthetic_fixture` with **no source observation ID**. Thus a fictional search or detail test cannot be misreported as an observed original-site behavior. Even matching an operator-labelled observed filter is an **illustration, not original-site verification**.

## Inputs and security checks

1. Original `ObservationBundle` JSON and its local evidence root. Existing `verify_manual_trace` rereads the sanitized manual-test JSON and checks source observation/evidence IDs, action, and typed before/after state. Operator-reported observations are **unverified**.
2. An existing generated `astra-synth-*` directory directly under system temp with 9 files from the previous `manual_trace_pipeline`, including `data/manual_pipeline_report.json`. The adapter reruns `check_generated_preview`, which verifies exact fixed Python/HTML template bytes, fixture SHA, blocked preflight trace and a dozen synthetic API/SQLite checks **before any generated code is imported by this adapter**.
3. `FeatureAcceptancePlan` JSON with the SHA-256 of the original observation, the prior pipeline report and the independent synthetic fixture. It holds up to 30 uniquely identified acceptance cases, typed route params and explicit expected IDs/status. Wrong/stale hashes, mismatched manual trace/feature, wrong expected ordering/status, invalid parameters, altered code or unknown fields fail closed.
4. For each accepted case, the adapter independently computes the expected fixture subset, executes the corresponding `GET /api/items` or `GET /api/items/{id}` using FastAPI TestClient with **a new temporary SQLite database**, and checks exact IDs/order/status and synthetic marker. It does not interpret observed source formulas.

SHA-256 verifies local byte consistency, not publisher identity or consent; an attacker replacing both data and its hash is not authenticated. There is no reviewer identity, original-site assertion, customer access, codegen authorization or deployment approval. All such flags are always `false`, and existing `GenerationContract` stays `blocked_pending_review`.

## Reproducible example

Create a **new empty** system temporary folder named `astra-synth-*`:

```bash
OUT=$(mktemp -d /tmp/astra-synth-feature-XXXXXXXX)
python -m astra_contracts.manual_trace_pipeline \
  fixtures/synthetic_manual_filter_observation_20261019.json \
  fixtures \
  fixtures/synthetic_manual_filter_schema_20261019.json \
  fixtures/synthetic_generation_request_20261018.json \
  fixtures/synthetic_demo_catalog_20261018.json "$OUT"
python -m astra_contracts.feature_acceptance_adapter \
  fixtures/synthetic_manual_filter_observation_20261019.json \
  fixtures "$OUT" fixtures/synthetic_feature_acceptance_plan_20261019.json
```

The checked-in plan is tied to the provided **fictional sample fixture**. For other fictional fixtures and action records, regenerate the plan's fingerprints and specify independent expected item IDs; never reuse the sample hashes. `feature_acceptance_adapter` outputs JSON **to stdout only**; it does not change sources, reports or the customer's database. It writes only disposable SQLite files inside its own system temp test directory.

Example: eight feature cases pass (one source **illustration** filter plus seven **independent** synthetic fixture cases covering list, limit, Korean text search, literal `%` escaping, empty category results and detail 200/404). Original site behavior, reviewer identity, DB rights, code generation and deployment authorization all remain false.

## Validation and exclusions

- 2026-10-19: local Python 3.13 full pytest **407/407 PASS** (373 prior + 34 new), `compileall` PASS, new one-command CLI successful with 8/8 adapter checks in addition to 12/12 prior synthetic acceptance checks.
- Existing unrelated httpx `data=` deprecation warning. GitHub Actions not invoked; administrator-blocked Chromium was **not** retried.
- Reference-site semantics, browser graphical clicks, real captures, real schema DB read/write, migrations, automatic business logic synthesis and production deployment are not implemented here. In particular, this adapter cannot turn an invented expected result into a reviewed feature requirement or customer permission.

## Suggested next single unit

Extend the reviewed acceptance contract to a **separately declared** synthetic schema adapter for multiple category/field shapes, or obtain explicitly authorized source interactions for genuine cross-site behavior verification. Keep real DB/auth/deploy behind a separate human approval mechanism and do not claim source behavior is verified from synthetic success.
