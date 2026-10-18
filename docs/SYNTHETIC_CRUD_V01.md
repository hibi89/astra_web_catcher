# ASTRA p4 — disposable synthetic CRUD v0.1

The `astra_contracts.synthetic_crud.create_app()` function builds an **isolated** FastAPI app over a fresh SQLite database in a direct child `astra-synth-crud-*` directory of the operating-system temp root. It implements `GET /api/items`, `GET /api/items/{id}`, `POST /api/items`, `PATCH /api/items/{id}`, and `DELETE /api/items/{id}`.

This is **not** connected to original-site evidence, generated preview UI, user-owned database, credentials, or deployment. No source-site behavior or production approval is claimed. Every item is synthetic and ephemeral; callers must create a fresh temp directory and destroy it after testing.

Validation rejects unknown payload fields, bool-as-integer scores, out-of-range scores, invalid IDs, duplicate IDs, empty/null patches, writes to the primary key, unknown IDs, nonempty existing database paths, symlinked database paths, and paths outside the constrained temp directory. SQL uses bound parameters for values. Dynamic update column names come exclusively from the strict `Patch` schema. SQLite writes are transactional via context manager.

Run: `python -m pytest -q tests/test_synthetic_crud.py`.

Next: integrate this isolated CRUD API into a generated synthetic preview only after proving the preview's code and data are explicitly fictional. Production/customer DB authorization remains blocked.
