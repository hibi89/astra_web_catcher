# ASTRA second documented-control analogue: checkbox, 2026-10-19 KST

## Provenance and scope

Publisher's official Selenium [element interactions](https://www.selenium.dev/documentation/webdriver/elements/interactions/) tutorial documents a click on the checkbox named `checkbox_input` on its public [inputs](https://www.selenium.dev/selenium/web/inputs.html) example, then tests `is_selected() == False`. The cited demonstration is **documentation**, not an actual executed original-site interaction here. A human-curated excerpt is SHA-256 pinned by `EXCERPT_SHA256`; this proves local bytes' integrity, not source authenticity or original live behavior. The original page's initial checkbox state was *not* independently inspected.

Two designs considered: modify earlier generated POST text form (small surface but risks changing its contract), or build a separate independent checkbox demo (slightly more code, preservation-friendly). Chosen: independent additive module and an isolated generated app. Existing form generator and customer files are unchanged.

## Generated local behavior

- `python -m astra_contracts.public_checkbox_analogue` is dry-run, offline and non-writing by default.
- `python -m astra_contracts.public_checkbox_analogue --generate` creates a new `astra-public-checkbox-*` child of OS temp; refuses existing, symlink and non-temp destinations and fails before generation when evidence is missing or tampered.
- Start within the generated folder: `python -m uvicorn app:app --host 127.0.0.1 --port 8020`, then open `http://127.0.0.1:8020/`.
- The demo initially displays a locally authored checked box. Its own JS `change` handler updates an accessible state element to `Unchecked` on uncheck and `Checked` on re-check. The checked default is a *local demo choice*, not a proven property of the original.
- Only `GET /`, `/controller.js`, `/health`; no external requests, form submission, session, DB, or write API. CSP disallows network resources other than self script. No original source/HTML copied.

## Verification and strict limitations

Tests: `python -m pytest -q tests/test_public_checkbox_analogue.py` (local FastAPI/TestClient, Node DOM simulation, negative guards, dry-run), plus live Uvicorn HTTP smoke separately. This does not amount to visual browser E2E. Original live click, original HTTP behavior, source authenticity, customer DB/API access, and deployment remain **unverified/unauthorized**. `GenerationContract=blocked_pending_review`; no changes to main or protected original generator.
