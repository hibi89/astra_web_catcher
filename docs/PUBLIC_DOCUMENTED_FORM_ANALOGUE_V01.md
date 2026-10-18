# ASTRA p4 — first public-doc-grounded independent functional analogue (v0.1)

## Why this change exists

The previous public-reference work only recorded readable site elements and Selenium's official explanation. The locally available browser had an administrator block, and the current container cannot resolve the original site's hostname (single `requests.get(..., timeout=5)` probe returned `NameResolutionError`). The web's read-only retrieval **does** show Selenium's published form at `https://www.selenium.dev/selenium/web/web-form.html`, its official how-to at `https://www.selenium.dev/documentation/webdriver/getting_started/first_script/`, and a separately opened result page `https://www.selenium.dev/selenium/web/submitted-form.html` containing `Form submitted` and `Received!`. **None of those requests submitted a form, clicked a button, captured browser screenshots, or verified the site's actual HTTP method**.

This unit deliberately pivots to a useful, narrow proof: **take a hash-pinned observed control + publisher-documented behavior, create a local independently authored app, and test the app's functionality against that published behavior.** It is a *functionally analogous* toy example, not a claim that the original page was automatically reconstructed.

## Input and restrictions

- Inputs: the prior `PublicPageNote` with the SHA-256 of both authored excerpts and recorded evidence IDs. The labels `Text input`, `Submit`, field selector `my-text`, and result `Received!` must be explicitly present. The expected URLs are fixed to the official Selenium public demonstration and its own publisher documentation.
- Generator refuses forged approval flags, altered hashes, unsupported URL or selector, output symlinks and pre-existing or non-system-temp destinations. No arbitrary HTML, JavaScript, external webpage code or owner data is copied into the output.
- Output: four files in a new `astra-public-form-*` system temp directory: `app.py` (independent FastAPI demo), `README.md`, `requirements.txt`, `provenance.json` (all authority claims false and excerpts' SHA-256 pinned).
- Local form: `GET /` displays input `my-text` and Submit; **our own implementation choice** uses `POST /submit`, validates a bounded single URL-encoded field, returns independently authored HTML with `Form submitted` and `Received!`. The original site's actual HTTP network contract is **not known**. `GET /health` explicitly marks `original_site_interaction_verified=false`.
- Invalid forms: wrong media 415; too-large body 413; duplicate, missing, unexpected fields / malformed encoding / unsafe values 422. Submitted values are not returned to page, logged, or stored by code. The app contains no database and makes no external requests.

## Reproduce locally

From repository root: `python -m scripts.build_public_form_analogue` (dry-run, no files), then `python -m scripts.build_public_form_analogue --generate` (creates an isolated temporary directory). In the generated directory run `python -m uvicorn app:app --host 127.0.0.1 --port 8019`; visit `http://127.0.0.1:8019`. For tests: `python -m pytest -q tests/test_public_form_analogue.py`.

## Verification boundaries

- `offline_reconstruction_functional=true` if the independent local HTTP form produces the expected response.
- `original_live_click_verified=false`, `original_form_method_verified=false`, `source_html_copied=false`, `owner_db_access_authorized=false`, `production_ready=false`, `deployment_authorized=false`, `GenerationContract=blocked_pending_review`.
- Do not promote the above to source-site functional equivalence or generalized URL→app generation. The fixed example demonstrates exactly **one** documented interaction, not arbitrary input URLs.
- No administrator-blocked browser retries, GitHub Actions, customer DB/API, original repository `main`, or deployment.
