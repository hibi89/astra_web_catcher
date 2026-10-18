# ASTRA Step 4-B / Unit 1 — evidence → draft functional specification

**Status:** implemented as an **offline, deterministic, read-only draft transformer**, not a runnable website generator and not an approved DB/API mapping. This is generic ASTRA tooling. The Japanese nail dashboard is only a regression case.

## Alternatives and choice

| Approach | Build/operating cost | Maintenance | Risk | Decision |
| --- | --- | --- | --- | --- |
| LLM interpretation of observation prose | External API cost and nondeterminism | Prompt drift / testing overhead | Can hallucinate unobserved behavior | Defer |
| Typed, deterministic Pydantic transformation | No external calls; existing dependency | Reuses ObservationBundle | Does not discover behaviors beyond supplied evidence | **Selected for v0.1** |

## Inputs / outputs

Input: a validated `ObservationBundle` JSON (schema 1.0). Output: **JSON to standard output**, never an implicit file write. Output has a stable SHA-256 fingerprint of canonicalized validated source data; the fingerprint is *not* proof that the historic observations were accurate.

- Only `observed` records become **candidate features**, each with its source observation ID, evidence kind/reference, claim, and changed *shared* before/after UI fields. Unchanged fields do not imply an event. One-sided fields are excluded from change detection, not guessed.
- `inferred` and `unknown` records become `unresolved`, preserving claims and named fields. They **never** automatically become implementable features.
- All feature review statuses remain `requires_review`. The overall draft has `implementation_ready: false` and `db_api_mapping_status: not_started`.
- All approval gates are `pending`: behavior review, DB/API mapping, authorization before external writes/deployment, and formula review when a basic-aggregate observation exists.
- Evidence sourced only from archived text is marked `archived_secondary`; direct source references are `reported_direct_not_independently_verified` — neither implies live browser or API verification.
- This unit proposes **no endpoints, table names, formulas, data migrations, code generation or live networking**.

## Run from repo root

```bash
python -m astra_contracts.functional_spec fixtures/jp_nail_brand_filter_observation_20261018.json
python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py
python -m compileall -q astra_contracts tests
```

Reference example: `fixtures/jp_nail_functional_spec_draft_20261018.json`. It has **1 filter candidate**, **2 unresolved claims**, **4 pending approval gates** and includes zero vs null distinctions. The CLI prints to stdout; if persisting with shell redirection, use a new filename and never overwrite a user file.

## Safety and limitations

The validator checks structural evidence IDs, certainty categories, simple secret-key patterns and obvious unsafe source URLs, **not** underlying truthfulness, sensitive prose or whether an attached document exists. It cannot infer browser handlers, n8n connectivity, API paths, KPI denominators, databases, privileges, or reliable interaction causality. Before generating code, a human must confirm desired behavior, provide owned schema/API contract and approve any proposed changes. Original `/shop`, `/jobs`, research branches, user data and production are untouched.

**Next single task after this unit:** Step 4-B user-owned DB/API mapping *contract* and discrepancy report, with explicit approval gates; no DB mutations. Do not combine this unit with that next step.
