# ASTRA p4 — Inactive observed mapping review panel (v0.1)

## Exact deliverable

`astra_contracts/mapping_review_ui.py` consumes the prior **offline** observed-feature-to-explicit-field traceability report. It extends a **generated synthetic FastAPI preview** with an optional local entrypoint `app.mapped:app`:

- `GET /preview-mapped`: the original fictional sort/filter UI plus a distinct *review-only* table.
- `GET /api/review-manifest`: one hash-pinned list of traceability findings, where **every** candidate and blocked finding has `enabled=false`.
- The existing generated `/preview` and `/api/rows` generic fictional query features are preserved. A review-only candidate is **not** automatically applied, selected, or considered an authorized workflow.

In the attached acceptance examples, fictional products expose a `family=colors` *candidate (unapproved)* and tickets expose a `lane=Open` *candidate (unapproved)*. Both previews also display the prior archived brand observation as `archived_secondary_only`. All mapped controls remain disabled; the archives do **not** become source behavior evidence.

## Reproducibility

From repo root:

```
python -m pytest -q tests/test_mapping_review_ui.py tests/test_mapping_review_dom_simulation.py
python -m compileall -q astra_contracts tests
```

A new verified temporary preview can be constructed using the prior `generate_integrated_preview`, `embed_synthetic_crud`, `embed_query_ui`, then `embed_review_ui` with exactly matching observed bundle, fictional schema, physical table, link plan, and local evidence. The returned report is only a synthetic generation artifact, not an authorization.

To serve the generated application *locally only*:

```
python -m uvicorn app.mapped:app --host 127.0.0.1 --port 8017
```

Open `http://127.0.0.1:8017/preview-mapped`. Never deploy publicly.

## Refusal and integrity gates

- Re-computes the existing observation/evidence-to-field mapping and verifies pinned source observation, table, schema and evidence digests; `source_kind=synthetic_fixture` only.
- Rejects stale source mapping report vs generated physical table, unrecognized preview columns, fake approval booleans, symlinks, existing output destinations and tampered trusted generated UI files.
- Distinguishes `synthetic_preview_candidate_unapproved` from a verified feature. Secondary archived findings have no preview values or active action.
- Every UI review action is an inert `button.disabled=true`. The script creates DOM nodes with `textContent`, no `innerHTML`, no `eval`, no request to `/api/rows` based on review mapping. The real query page remains separately usable for arbitrary fictional fields.
- The generated server pins the exact review HTML and JSON file SHA-256, validates all `enabled=false` and permission flags at response time, and rejects tampered files with HTTP 503.
- The new `app.mapped:app` refuses to load if `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY`, preventing accidental combination of review UI and writable sandbox.

**Limitations:** Chromium real browser rendering remains administrator-blocked; the JavaScript manipulation tests use Node DOM simulation, plus separately checked HTTP. Evidence digest verifies only bytes, not whether any claimed original-site interaction occurred. Original site analysis, owner DB/API, actual user authorization, permission review, production app generation and deployment remain **unverified**. `GenerationContract` remains `blocked_pending_review`. No real-data input, source scraping, GitHub Actions or protected-path edits are performed.

## Next bounded unit

Obtain explicitly authorized **first-hand** observation traces of a chosen reference URL (real before/after interaction) and a verified owner schema, or improve the review UI's visible provenance ledger without granting approval. Do not infer a real DB mapping from field-name similarity or connect owner data without consent.
