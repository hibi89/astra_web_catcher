# ASTRA p4 — two-control CLI real-source validation (2026-10-19 KST)

## Scope

Bounded task: close the previous review-only comparator's **unverified default CLI execution** gap. No application feature, original website, customer database, or protected main changed.

The attached ChatGPT container retained the previous local checkbox/reviewer/test/fixture workspace `/mnt/data/astra_checkbox_work`. GitHub connector fetched the missing `astra_contracts/public_form_analogue.py` from the existing feature branch; that module was restored byte-for-byte to the workspace and verified using `git hash-object`. Both publisher evidence excerpts for text form and one checkbox evidence excerpt were already present and SHA-256 matched the locked expected values.

This is a **complete set of source files needed for the comparator**, not a complete Git repository checkout and not a claim that the whole feature branch or all 739 tests were run.

## Executed checks

1. `git hash-object astra_contracts/public_form_analogue.py` → `82670b1e797d2473fe7c3262f8e28b282afd13c5` = GitHub published blob.
2. `python -m astra_contracts.mechanism_contract_review` from local workspace → process success and JSON `report_version=0.1`, `control_count=2`; checked `checkbox_input/change/Checked / Unchecked/own_local_dom_event` and `my-text/submit/Received!/own_local_http_post`.
3. JSON explicitly has `publisher_authenticity_verified=false`, `original_site_live_interaction_verified=false`, `customer_db_or_api_authorized=false`, `generation_authorized=false`, `deployment_authorized=false`, `network_used=false`, `files_written=false`, and `generation_contract=blocked_pending_review`.
4. `python -m pytest -q tests/test_mechanism_contract_review.py tests/test_public_checkbox_analogue.py` → **33/33 PASS**; `python -m compileall -q astra_contracts tests` → PASS (Python 3.13.5).
5. Copied exactly the two source modules plus the three evidence excerpts into an isolated temporary root, used `--root` to re-run → **PASS**. Modified the copied checkbox excerpt and reran: exit code nonzero, **no success JSON stdout**, `evidence SHA-256 mismatch` reported → **PASS fail-closed tamper negative**. No edits to the source set.
6. Four local source blobs match GitHub: original text form `82670b1`, checkbox `ecf1239`, reviewer `966c125`, reviewer tests `030c555`. All three fixture SHA-256 values match the pinned comparator entries.

## Limits

- Python CLI was run in a **selected-file local workspace**, not a complete branch checkout. This nevertheless executes its real default pathway against byte-identical GitHub source+evidence inputs.
- No real original-site click, real browser before/after screenshot, customer DB or API binding, additional code generation, or production deployment.
- No `pytest` whole-project 739-case regression; this unit only 33 selected tests.
- No GitHub Actions invoked or Vercel changes made.
- Original `main` SHA before documentation work: `dc23ee604d02513c890615a3a98440c1ea8a5270`.
- Two-control comparator's success cannot grant generation authority. Keep `review_only_no_approval` and `blocked_pending_review`.

## Next bounded task

The comparator has passed its real file-input CLI checkpoint. Next action should target actual product proof rather than another synthetic widget: when authorized interactive browser is available, capture and independently verify **one** reference before/after behavior; otherwise, after explicit scope/data-owner approval, design a **read-only interface** for a user-owned example schema without accessing real data until approved. Do not retry administrator-blocked browser or perform unauthorized customer DB access. Overall roadmap completion estimate remains **~49%**.
