# ASTRA p4 — Synthetic generated-app acceptance, v0.1

## Purpose / boundary

One deterministic acceptance unit for **an ASTRA-created fictional preview**, after the pre-existing observation → synthetic-bridge generation. It does **not** implement original website logic, approve unverified evidence or user database bindings, or enable production app generation/deployment. The upstream `GenerationContract` remains `blocked_pending_review`.

## Problem discovered and repaired

The prior bridge advertised the example filter URL `/api/items?category=sample`, but the explicit synthetic test catalog contains `색상`, `기법`, `질감` instead. This is a *false-positive coverage risk*; an HTTP 200 with an empty result does not prove a filter works. The bridge now selects a URL from the **fictional input fixture**, percent-encodes the category, and applies the same technique to synthetic search and detail examples. No values are taken from the original website or its historical screens. Existing trace metadata remains `original_behavior_verified: false`.

## What the new acceptance runner checks

- Source code and HTML exactly match fixed, known synthetic templates before the generated Python module is loaded; missing files, symlinks and tampered templates fail closed.
- Validated demo input and bridge trace share the same SHA-256 identity; an altered seed or misleading trace route is rejected; the preflight still explicitly blocks independent real code generation.
- In-process FastAPI `TestClient` exercises health, root HTML, **exact** sorted listing, **nonempty** category-filter results with the correct subset, search, detail, absent-detail HTTP 404, invalid limit HTTP 422, literal `%` and `_` search handling, a trace-linked observed feature category and SQLite persistence across app reinitialization.
- Output is a `SyntheticAcceptanceReport` with twelve passed assertions on the supplied synthetic case. It is structurally impossible to set `original_behavior_verified`, `production_ready`, `user_database_accessed` or `original_generation_approved` to `true` in that validated report.
- Also tested a separate fictional job-list fixture with the same generator and acceptance code. No customer-owned schema, original-site URL, remote network, credentials or production DB is involved.

## Reproduction from repository root

```bash
python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py tests/test_data_mapping.py tests/test_generation_contract.py tests/test_synthetic_generator.py tests/test_synthetic_bridge.py tests/test_synthetic_acceptance.py
python -m compileall -q astra_contracts tests
```

To exercise the actual generated app, first run `python -m astra_contracts.synthetic_bridge` with the seven documented arguments (see `docs/SYNTHETIC_BRIDGE_V01.md`) and an existing empty `astra-synth-*` system-temp directory. Then:

```bash
python -m astra_contracts.synthetic_acceptance /tmp/astra-synth-example123
```

The runner never accesses a live website: it uses a disposable SQLite database in a separate temporary directory and in-process ASGI calls. An **additional manual automation check** started Uvicorn bound to `127.0.0.1`, then made actual loopback HTTP requests to health, root, listing, encoded Korean category filter, search, detail, nonexistent item and malformed limit; statuses were correct (200/404/422). This local HTTP evidence is distinct from, and does not imply, a graphical browser E2E.

## Results, 2026-10-18 KST

- Prior 152 tests + **18 new acceptance tests** = **170/170 PASS**; Python `compileall` PASS.
- Generated eight files; twelve acceptance assertions PASS, including nonempty filter coverage; independent fictional jobs fixture PASS.
- Actual local Uvicorn HTTP health/root/list/filter/search/detail 200, missing item 404, bad `limit` 422.
- `main`, `/shop`, `/jobs`, historical nail research/practice, user databases, permissions, source schemas, live services and deployment **unchanged**. No GUI browser/Playwright run was attempted because prior Chromium localhost restrictions were documented; do not call this browser E2E.

**Next one-unit candidate:** introduce an explicit reviewer decision record for evidence claims and field semantics (separate from the synthetic acceptance report), or test an additional previously unseen synthetic layout/behavior. Real integration requires independent user approval and a verified user-owned schema.
