# ASTRA p4 — pinned repository SQLite schema intake, 2026-10-19 KST

## Goal and scope

Bridge an **existing, user-controlled repository schema** into the project's earlier offline `OwnedSchemaDeclaration` shape without touching a real database or auto-mapping original website behavior.

The source is the existing fictional BookHarbor/CareerWay DDL file `migrations/001_initial.sql` from `hibi89/astra_web_catcher` main, Git blob **`5f5bdcb950dcfa0587b0deec2b7afb5e17f155bd`**, SHA-256 `147c7c8f139330599a22e13035b1baa05166c520757f1025e07f6f86ce2ae0bf`. The original file was not modified. This is a **repository-owned demo schema**, **not an actual customer's verified live schema**.

## Two approaches evaluated

| Approach | Runtime / API cost | Accuracy and maintenance |
| --- | --- | --- |
| Regex/heuristic SQL parser | Low, no external API | Easy to misinterpret constraints, composite keys, and SQLite semantics; bespoke parser grows |
| **Pinned-file + in-memory SQLite introspection** (selected) | Low, no external API/LLM; uses local SQLite only | Reuses SQLite's own DDL interpretation; exact Git blob SHA gate prevents changed/unreviewed DDL from executing. Requires reviewing the SHA after legitimate migration changes |

No live DB connection, API request, external website, model call or persistent write occurs. A fresh **in-memory** SQLite schema is instantiated from the exact, pinned migration. This does execute the already-reviewed local DDL inside memory; no unpinned scripts execute.

## Output and exclusions

Command from a full feature-branch checkout:

```bash
python -m astra_contracts.owned_migration_schema
python -m pytest -q tests/test_owned_migration_schema.py
python -m compileall -q astra_contracts tests
```

The first command writes JSON to stdout only:

- 11 schema tables discovered from the pinned DDL.
- Only 4 allowlisted *fictional demo resources* exposed: `categories` (2 fields), `products` (7), `companies` (3), `job_postings` (10), **22 column declarations** total.
- 7 account/authentication/order/user-owned related tables **excluded** from the report. No user rows, passwords, session tokens, order data or actual runtime DB accessed.
- `declaration.schema_version=0.1`, `source_kind=synthetic_fixture`, `resources[*].kind=db_table`, `bindings=[]`. No automatic semantic bindings. Integer SQLite storage flags such as `is_closed` remain typed `integer`, not inferred `boolean`.
- `live_database_schema_verified=false`, `customer_database_accessed=false`, `mapping_semantics_verified=false`, `authorization_granted=false`, `generation_authorized=false`, `deployment_authorized=false`, `external_network_used=false`, `files_written=false`; `generation_contract=blocked_pending_review`.

The module refuses absent/symlinked/oversized files and a changed Git blob before loading any DDL. It rejects unexpected table counts, public table column drift and unknown SQLite storage types. No update or deletion of `data/app.db` is performed. Output is review metadata and is **not** a live owner-data integration or approval.

## Verification

- Python 3.13.5 isolated workspace with byte-exact GitHub migration: **17/17 new isolated tests PASS**, **1 integration test SKIP** because the full feature branch's `astra_contracts.data_mapping` dependency was not mounted into the local *selected-file* workspace. `python -m compileall -q astra_contracts tests` PASS; CLI JSON output PASS.
- Tests cover pinned Git SHA, real SQLite table schema, 4 resource/22 field projection, sensitive table suppression, field nullability/storage fidelity, deterministic no-write execution, changed DDL/attach/drop/view rejection, symlink/path/size rejection, strict typing, CLI fail closed. No browser or live original site testing.
- The newly uploaded source and test Git blobs exactly match the locally tested files: `b2cc785ff4593112721642922979fc35ca297d27` and `8a72284810d94bb5e5045e437c4bf010e9d49f0c`.
- **Not verified:** full-checkout Pydantic `OwnedSchemaDeclaration` integration, 739+ whole project suite, production runtime, original third-party site behavior or any real customer DB/API.

## Next meaningful unit

On a **complete** feature checkout, run the skipped data-mapping-model compatibility test and the existing `tests/test_data_mapping.py` targeted regression to verify the declared JSON against the real prior Pydantic model. Separately, actual customer DB mapping needs an authorized, sanitized owner-supplied schema and explicit mapping approval. Do not substitute fictional fixture progress for an end-to-end demonstration. Overall conservative roadmap estimate **49% unchanged**.
