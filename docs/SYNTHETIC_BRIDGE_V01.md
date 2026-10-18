# ASTRA Synthetic Preview Bridge v0.1

Purpose: bridge a validated historical UI functional-spec draft to an independent fictional-only test application. The bridge revalidates the synthetic declared schema, recomputes the mapping report, and compares the existing fail-closed GenerationContract to a fresh preflight. It preserves blocked_pending_review; actual site behavior, customer data, approvals, source APIs, database writes and deployment remain out of scope.

Input CLI: python -m astra_contracts.synthetic_bridge SPEC SCHEMA REPORT CONTRACT REQUEST SYNTHETIC_FIXTURE EMPTY_TEMP_FOLDER

The last argument must be an existing empty astra-synth-* directory immediately under the system temp root. It creates seven fixed FastAPI/SQLite/HTML demo files and an eighth non-executable data/astra_preview_trace.json, which reports source fingerprints, feature IDs, fictional smoke routes, unresolved items and mapping discrepancies. A simulated category never asserts faithful reproduction of the original site; unverified calculations are not implemented.

Local acceptance (2026-10-18 KST): full focused pytest suite 152/152 PASS (134 existing + 18 new); compileall PASS; generated demo test PASS; actual Uvicorn localhost GET /, /health, /api/items, category filter, text search, item detail = HTTP 200; unknown id HTTP 404. Brand-filter sample: one simulated filter, two unresolved observations, seven mapping issues; generation authorization stays false.

Safety tests cover report and contract tampering, changed specs, non-synthetic owned schema rejection, unsupported stacks, nonempty paths and non-temporary destinations. The CLI never connects to real websites or databases. Source paths: astra_contracts/synthetic_bridge.py, tests/test_synthetic_bridge.py. This is not the completed generic URL-to-application generator.
