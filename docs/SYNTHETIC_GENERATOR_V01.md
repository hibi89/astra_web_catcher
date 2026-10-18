# ASTRA Step 4-C — synthetic-only runnable preview (unit 2)

**Scope:** This is a genuine but deliberately isolated artifact generator, not the ASTRA general code-generation pipeline. It operates on an explicit *fictional* `SyntheticDemo` manifest, **not** on `FunctionalSpecDraft`, `OwnedSchemaDeclaration`, `MappingReport`, or `GenerationContract`. The earlier fail-closed contract remains unchanged and returns `blocked_pending_review`.

## Design choice

- Option A: directly generate from the unapproved observation/mapping reports. Rejected: missing original formulas, unapproved bindings and secondary observations would be treated as trusted.
- Option B: only accept a separate, explicit, bounded synthetic fixture, write inside a caller-created empty system-temporary directory, and generate an independent, minimal read-only local app. **Selected.**

## Inputs and protections

`SyntheticDemo` requires `schema_version=0.1`, `source_kind=synthetic_fixture`, `run_mode=temporary_demo_only`, a title and 1–100 explicitly provided rows. Rows have bounded `id`, `title`, `category`, integer `score`; no arbitrary source code, URLs or SQL. This is a syntactic contract and does not independently prove a submitter honestly labeled the data synthetic. Only use intentionally fictional values.

`generate_synthetic` accepts an **existing empty** direct child of the system temporary directory with name prefix `astra-synth-`; symlinks, nonempty directories and any other destinations are refused. All files are created using exclusive mode (`x`) and are never overwritten. Nothing is deployed, connected to customer services or written into the repo. Output files: `app/__init__.py`, `app/main.py`, `app/index.html`, `data/seed.json`, `tests/test_app.py`, `requirements.txt`, `README.md`.

The generated independent webapp provides a tiny HTML/JS UI, FastAPI `GET /health`, `GET /`, `GET /api/items` (optional `category`, `q`, bounded limit), `GET /api/items/{id}`, and *local demo only* SQLite persisted in its own generated folder. It has **no write API or login**, uses SQLite bound query parameters and client `textContent` for display; it is **not production hardened**. It neither copies the reference site's source nor implements its formulas. The demo uses a fixed generic schema and code template, not an inference from the 2026 OHORA dashboard.

## Reproduce

From the ASTRA contracts repo root:

```sh
DIR=$(mktemp -d /tmp/astra-synth-XXXXXXXX)
python -m astra_contracts.synthetic_generator fixtures/synthetic_demo_catalog_20261018.json "$DIR"
cd "$DIR"
python -m pytest -q tests/test_app.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8017
```

Windows users can use `tempfile.mkdtemp(prefix="astra-synth-")` from Python and pass that path; the generator resolves the actual system temp path. Only run on a local machine with compatible Python / FastAPI dependencies. Demo app ZIP is also attached in the implementation conversation.

## Evidence and limitations

- Local test command: `python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py tests/test_data_mapping.py tests/test_generation_contract.py tests/test_synthetic_generator.py` → **134/134 PASS** (111 prior + 23 new).
- New app generated 7 files; generated self-test 1/1 PASS; independent fictional job-list case 1/1 PASS; compileall PASS.
- Actual Uvicorn bound to `127.0.0.1` returned HTTP 200 for health, HTML page, list, category filter, text search, one item detail; missing item 404. SQLite record persistence was verified. These are **real local HTTP** checks; manual GUI/Playwright browser rendering was not performed.
- No customer-owned DB, account, third-party API, secrets, original apps or source research modified. **Only synthetic preview code has been generated**, not a general URL/observation → independent app implementation; Step 4-C generic adapter/codegen and Step 4-D automation/E2E still pending.
- Next `ㄱ` may build a narrowly scoped bridge from reviewed feature-spec and explicit mapping to an **isolated test-data** app generator after adding explicit authorization/review workflow; do not remove the current blocked preflight or authorize production implicitly.
