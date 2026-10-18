# ASTRA p4 — isolated local reviewer-opinion UI v0.1

**Scope:** A runnable **localhost-only** UI for manually documenting evidence and field-mapping opinions. Not a customer website or authority/approval system. It consumes `FunctionalSpecDraft`, `OwnedSchemaDeclaration` and `MappingReport` created earlier. `build_packet()` recomputes the declared mapping before serving anything; stale/altered mappings fail immediately. It does not connect to the observed reference website, customer database, private API, remote authentication or deployment.

## Interface

- `/`: responsive Korean-language UI with grouped cards for (1) observed screen behavior, (2) unresolved behavior/formulas and (3) field semantics. The archived OHORA demonstration contains **13 cards** (1 + 2 + 10).
- Each card allows an optional reviewer decision (`needs_more_evidence`, `supported_as_proposal`, `rejected_for_target`), rationale (8–1,200 characters) and references **only from the attached evidence list**. The UI disables *supported* for historical-only behavior, unresolved behavior and incompatible/unmapped fields. Server validation remains authoritative.
- Search/group filter retains in-progress edits. Reviewer label is only an **unauthenticated claim**. No review is attributed to an actual user unless the user directly submits it; synthetic tests use an expressly fake label.
- `/api/packet`: read-only JSON packet and per-session local token; `/api/opinions`: validate and save an unverified opinion; `/api/opinions/{id}`: retrieve a saved opinion using an unpredictable 24-character record ID and the session token. Saved records remain in an isolated system temporary directory (`astra-review-*`), are written **exclusively**, and never overwrite another record. Storage is not persistent customer infrastructure.
- All authorization flags in `ReviewRecord` remain **false**, even if every card has an opinion. This service cannot approve schema migrations, DB access, code generation, original behavior or deployment; `GenerationContract` remains `blocked_pending_review`.

## Run from repository root

```bash
python -m astra_contracts.review_ui fixtures/jp_nail_functional_spec_draft_20261018.json fixtures/synthetic_owned_schema_mapping_20261018.json fixtures/synthetic_mapping_report_20261018.json --port 8018
```

Open `http://127.0.0.1:8018/` in **your own** browser. For Windows PowerShell the same Python command is valid. Requires the existing project's Pydantic, FastAPI and Uvicorn dependencies. The HTTP server binds to loopback only and is not configured for external access. A temporary opinion folder path prints at startup; copy records out manually before its cleanup if retention is needed. **Do not enter credentials, customer secrets or personal information into review rationale.**

## Safety and scope boundaries

- Host and `Origin` checked, token required for record creation and readback, no CORS, conservative CSP and `no-store` headers. Inputs capped, Pydantic strictly validated; HTML UI renders untrusted data via `textContent`, not `innerHTML`.
- This is a local tool and not a hardened multi-user service. A process running with the same local user permissions may access the temporary files. Do not expose on a LAN, reverse proxy or public host.
- No database, mutable external service, file migration, production schema, or original website interaction. Tests use only **synthetic** schema and an archived report: raw screenshots, original formulas and API endpoints remain unverified.

## Verified evidence (2026-10-18 KST)

- `python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py tests/test_functional_spec.py tests/test_data_mapping.py tests/test_generation_contract.py tests/test_synthetic_generator.py tests/test_synthetic_bridge.py tests/test_synthetic_acceptance.py tests/test_reviewer_decisions.py tests/test_review_ui.py`: **213/213 PASS** (193 previous + 20 new).
- `python -m compileall -q astra_contracts tests` PASS; `node --check astra_contracts/review_ui.js` PASS.
- Real Uvicorn `127.0.0.1:18766` via Python HTTP client: GET `/`, `/review.js`, `/review.css`, `/api/packet`; POST one fictional `needs_more_evidence` record; GET same record → HTTP 200, correct readback and approval `false`.
- Chromium Playwright `page.goto()` to localhost raised `net::ERR_BLOCKED_BY_ADMINISTRATOR` due the test environment's browser policy. **Graphical click E2E remains unverified, not PASS**. Do not repeat previously blocked navigation without a changed environment.

**Next bounded unit:** On an authorized local browser, verify interactive item filtering, keyboard accessibility and saved opinion readback, or design a manual reviewed-decision export/import package with explicit trust boundary. Real DB/API mapping and production generation must still be independently authorized and tested.
