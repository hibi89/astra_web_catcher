# ASTRA — Observation Evidence Contract v1 (2026-10-18)

## Design decision

- Option A — JSON Schema file + custom Python validator: language-neutral but duplicates cross-reference logic and introduces another maintained validation path.
- Option B — Pydantic 2 model + exported JSON Schema: uses a dependency already in requirements.txt and gives a single executable source of truth for Python clients; JSON Schema is provided for downstream tooling.
- **Selected B**, because ASTRA's current runtime is Python/FastAPI, implementation overhead is lower and evidence-reference validation needs model-level checks. No new paid APIs, network, LLM, or background tasks.

## Scope and safety

This is one isolated Step 2 / Step 4-A foundation unit. It validates a *human-supplied, sanitized* account of an allowed website's visible behavior. It does **not** browse a URL, collect screenshots, generate functionality or code, modify an app, call an API, access a database or write user data.

Existing shop/jobs app, research nail dashboard and experiment nail practice must remain unchanged. The fixture is **synthetic**: the evidence paths are placeholders, not assertions that screenshots exist.

## Input representation

- Bundle: schema_version 1.0, sanitized site_url, scope, timestamp with timezone, evidence array, observations array.
- Evidence: unique ID, screenshot / DOM text / user demonstration / sanitized network / manual test kind, relative source path, timezone-aware capture timestamp, short notes.
- Observation: unique ID, navigation/list/search/filter/detail/create/update/delete/basic_aggregate feature, claim, observed/inferred/unknown certainty, evidence IDs, optional action, before/after scalar UI values.
- **Observed** requires referenced evidence; **unknown** may not claim a referenced observation source. References must resolve and be unique. **Inferred** is never silently promoted to observed. Missing measurements are null, not zero.
- Embedded URL credentials, common credential query parameters, suspicious state keys, raw nested response objects, unsafe evidence path traversal and extra fields are rejected.
- Validator does NOT check if referenced files exist or whether a statement is substantively true. Human source review remains essential. This is not general-purpose PII or secret detection.

## Commands from repository root

    python -m astra_contracts.observation validate fixtures/observation_brand_filter.json
    python -m astra_contracts.observation schema > observation.schema.json
    python -m pytest -q tests/test_observation_contract.py

The CLI returns 0 for valid JSON observations and 1 for validation errors. The exported JSON Schema describes field structure, **not** every Python cross-record rule: rely on the Pydantic validator for uniqueness and evidence link enforcement.

## Acceptance and remaining work

- Tested locally on Python 3.13, Pydantic 2.13.5, pytest 9: **19/19 PASS**, sample CLI PASS, schema export and compileall PASS.
- Commit source, fixture, tests and this guide on a branch; re-read GitHub contents and verify the commit. Existing original apps and databases remain unchanged.
- **Not yet implemented:** observation acquisition, conversion of historic evidence, Step 4-B automated feature specification, user DB/API mapping, generated service and browser E2E. Next ㄱ should pick just one of these next confirmed units.

