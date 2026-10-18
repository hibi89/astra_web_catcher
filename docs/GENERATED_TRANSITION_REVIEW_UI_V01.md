# ASTRA p4 — Generated before/after provenance review UI v0.1

## Exact delivered boundary

`astra_contracts.transition_review_ui` builds a read-only **provenance ledger panel** on top of the existing fictional `/preview-mapped` app. The new generated entrypoint is `app.transitions:app`, serving `/preview-transitions` and `/api/transition-ledger`. Existing `/`, `/preview`, `/preview-mapped`, `/api/review-manifest`, `/api/rows` remain unchanged; no permitted operations are silently enabled.

A `TransitionLedger` is rebuilt using the existing `capture_transition_ledger.build_transition_ledger()` *at installation time*, checking the registered before/after **file bytes**, manifest hashes, order, observation IDs, and claimed state transition. This does **not** check screenshot authenticity, whether the operator visited the site, meaning of a screenshot or DOM snapshot, true UI behavior, or any customer consent.

`build_display_manifest()` projects only evidence linkage IDs, claimed field, status and fixed explanatory text. Claimed before/after **values and original snapshot bytes are not copied** into the generated project. A SHA-256 hash binds the projected report to the ledger rebuilt during installation. The app verifies static JSON/HTML, the prior mapped assets and the synthetic physical fixture hashes at **each HTTP request**. It does not re-open external intake source bytes at request time and says so explicitly.

## UI and fail-closed policy

The new page includes both the prior disabled mapping panel and a second table headed **클릭 전·후 증거 장부**. Each row shows transition ID, observation ID, two capture IDs, asserted changed field, structural result, and a permanently disabled **근거 검토 필요** button. `paired_bytes_present_unverified` is never displayed as site verification or semantic approval. All permission flags and per-row `enabled` flags are hard-fixed to `false` through strict models, generated endpoint guards, and client-side validation. Rendering uses `textContent`, never `innerHTML`. No result invokes a mapping API to change an app state.

Tampering with the saved ledger JSON, transition HTML, old mapped code/HTML/manifest, or physical fixture returns HTTP **503** on the new routes. Existing outputs, symlinks and non-isolated preview destinations are rejected before installation; stale or corrupted captured bytes stop installation before writing new files. If `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY` is set, the read-only overlay refuses startup. **Never publish this demonstration to the Internet.**

## Reproduce locally (fictional data only)

The test example uses fictional `fixtures/synthetic_transition_pair_*_20261019.json`, along with corresponding `fixtures/evidence/synthetic_transition_*_20261019.txt`. Register these into a fresh `astra-capture-*` OS-temp intake folder, and create the existing synthetic generated preview, CRUD wrapper (off by default), query UI, mapped review UI, then call:

```python
from astra_contracts.transition_review_ui import embed_transition_review_ui
report = embed_transition_review_ui(generated_root, observation_bundle, intake_dir, transition_plan)
```

Launch in the **generated** project directory: `python -m uvicorn app.transitions:app --host 127.0.0.1 --port 8017`, then visit `http://127.0.0.1:8017/preview-transitions`. Its data is solely synthetic. Original-site browser interaction was not independently verified; administrator-blocked Chromium was not bypassed or retried.

## Acceptance and limits

- New Python strict-policy, integration, tamper, and negative tests; optional Node.js DOM script simulation, not graphical-browser testing.
- Actual localhost Uvicorn GET `/preview-transitions`, `/api/transition-ledger` and preexisting routes tested with status and output checks.
- No customer database/API, private browser session, credential, source code retrieval, approval escalation, production generation, or deployment.
- `GenerationContract` stays `blocked_pending_review`; existing `main` is unchanged.

Next engineering priority should be verified authorized real-site evidence acquisition and substantive semantic review, rather than further synthetic widgets. This panel does **not** advance the core goal's real-world completeness by itself.
