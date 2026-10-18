# ASTRA Step 4-C — independent generation preflight contract v0.1

## Scope

One **offline, fail-closed planning contract** for a future independent application generator. This is **not** an implementation of code generation, browser inspection, database integration, approval collection or deployment. It does not emit executable code or modify files; the only output is JSON on stdout.

## Alternatives and selected approach

- Generate a scaffold immediately when some declared fields appear compatible: faster superficially but unsafe, because a name/type match does not establish metric semantics, ownership, consent or authorization.
- **Selected:** immutable `contract_only` manifest and hard-blocked safety preflight. The generator contract can be reviewed before any independent implementation or source write is permitted.

## Inputs

1. `FunctionalSpecDraft` v0.1 — observed candidate features and unresolved behavior.
2. `OwnedSchemaDeclaration` v0.1 — explicitly documented owned DB/API fields and user-supplied bindings; this is **not** a live connection.
3. `MappingReport` v0.1 — must precisely match a **fresh recomputation** from (1) and (2), preventing a modified report from suppressing conflicts.
4. `GenerationRequest` v0.1 — only `mode=contract_only`, `scope=new_isolated_project`, stack `fastapi_sqlite` or `nextjs_prisma`, safe canonical *relative* destination path. Absolute paths, `..`, hidden/reserved components and shell-sensitive characters are rejected.

## Deterministic JSON output

`GenerationContract` provides SHA-256 fingerprints of validated inputs, a list of observed candidate IDs, a **non-executable proposed file-path manifest**, mandatory preflight blockers, original approval gates and outstanding future reviews. Its status is always `blocked_pending_review`, and `code_generated`, `files_written`, `deployment_permitted`, `data_mutation_permitted` and `approval_verified` are all constant **false**. Even a structurally clean document-only mapping is **not sufficient for permission**. It never accepts an affirmative approval parameter.

The sample references the **historical Japanese nail UI observation** and an invented **synthetic** DB/API schema. Its preflight has 1 observed feature candidate, **8 blockers**, 7 inherited gates and 4 future review requirements. No actual customer database or current website was inspected. An additional Next.js/Prisma manifest is covered by tests, but no Next.js or FastAPI files are created.

## Verify from repository root

```bash
python -m astra_contracts.generation_contract fixtures/jp_nail_functional_spec_draft_20261018.json fixtures/synthetic_owned_schema_mapping_20261018.json fixtures/synthetic_mapping_report_20261018.json fixtures/synthetic_generation_request_20261018.json
python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py tests/test_data_mapping.py tests/test_generation_contract.py
python -m compileall -q astra_contracts tests
```

Expected local result for this unit: **111/111 PASS** (prior 71 plus 40 contract tests), CLI JSON matches `fixtures/synthetic_generation_contract_20261018.json`, compileall PASS. These tests cover input/report tampering, unsupported stacks/modes, unsafe destination paths, approval forgery, deterministic output and isolated planning; they do **not** establish actual browser or production behavior.

## Limits and next unit

All existing `/shop`, `/jobs`, nail research/practice, data and `main` remain untouched. This isolated branch should be reviewed before merging. A next `ㄱ` may implement a *synthetic, isolated artifact generation prototype* or a review workflow, **separately** from this contract. Connecting to a user's real schema, source changes, tests with real data, code execution and deployment require distinct permission and verification. Never claim this contract already implements a runnable generator.
