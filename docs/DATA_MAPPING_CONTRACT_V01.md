# ASTRA Step 4-B / Unit 2 — offline owned-schema mapping diagnostics (v0.1)

## Purpose and choice

Use a **user-supplied schema declaration plus explicit field bindings**, then report missing mappings, missing resources, missing fields, scalar type conflicts, unknown types and nullability conflicts. This follows the user-approved principle that the user's schema is authoritative: ASTRA cannot silently add columns, assume endpoint semantics, infer KPI formulas, or mutate a live system.

Considered approaches:

- **Name-similarity auto-matching** saves input time but risks false matches and incorrect financial/engagement metrics. Rejected for this safety-critical first contract.
- **Explicit mapping manifest with deterministic diagnostics** requires a little human input but is offline, testable, transparent and cheap. Selected.

## Inputs and expected output

Input 1: the unapproved `FunctionalSpecDraft` produced by `astra_contracts.functional_spec` (schema v0.1).

Input 2: a **declaration** (`OwnedSchemaDeclaration`) with `source_kind` (`synthetic_fixture` or `owner_supplied_document`), `source_label`, resources (`db_table` or `api_response`), fields (`string`/`integer`/`number`/`boolean`/`unknown`, nullability), and explicit bindings keyed by `(observation_id, ui_field)`. This is a *document description*, not a DB connection or evidence of API access. It contains **no credentials, URLs, SQL, or real client data**. Users should remove personal information from documents before supplying them.

Output: read-only `MappingReport` JSON sent to stdout, including input fingerprints, each changed UI field and declared target, classification, counts, unresolved historical observation IDs and approval gates. Allowed classifications: `structurally_compatible_unapproved`, `unmapped`, `missing_resource`, `missing_resource_field`, `type_conflict`, `unknown_ui_type`, `nullable_conflict`. Integer is structurally compatible with number; boolean is not integer. A UI null against non-nullable field is a conflict. Zero stays distinct from null. `unknown` or mixed UI types are **not** auto-coerced. Duplicate entries and bindings to nonexistent feature fields are rejected.

**Structural compatibility is neither semantic equivalence nor approval**. The report intentionally hard-codes `schema_verified_against_live_system: false`, `mapping_approved: false`, `implementation_ready: false`, `status: review_only`. All seven review gates remain outstanding in the sample, including permission to change source schemas. No schema changes are suggested or executed.

## Reproduce from repository root

```bash
python -m astra_contracts.data_mapping fixtures/jp_nail_functional_spec_draft_20261018.json fixtures/synthetic_owned_schema_mapping_20261018.json
python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py tests/test_data_mapping.py
python -m compileall -q astra_contracts tests
```

Golden report: `fixtures/synthetic_mapping_report_20261018.json` (generated from the fixture). The fixture is **invented purely to test diagnostics**; it is not OHORA's DB structure. Expected findings: 10 changed UI fields, **3 structurally compatible but unapproved, 4 unmapped, 1 missing resource, 1 missing resource field, 1 type conflict**, plus 2 unresolved prior observations and 7 pending gates. Pure function and CLI, no network calls, no DB reads/writes, no user file overwrites. To retain a report, redirect stdout to a *new* path.

## Scope / blockers

Tests validate model behavior but cannot prove the actual customer's schema, ownership, field meanings, authorization, or formula correctness. A live DB/API mapping cannot proceed until the user supplies an **authorized and sanitized** schema description, resolves discrepancies and approves any changes. This unit does not touch the existing `/shop`, `/jobs`, research/experiment branches or original user data. Actual ASTRA flow `URL/observations -> functional spec -> code -> browser/API test` remains unconnected. Next `ㄱ`: advance to a separate, review-gated independent code-generation contract (or other next confirmed unit); do not execute live writes without approval.
