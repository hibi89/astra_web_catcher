# ASTRA p4 — public Selenium live-browser proof path (2026-10-19 KST)

## Goal and acceptance

Close the first-hand observation blocker without repeating the administrator-blocked container Chrome method. Instead, run **one** action on Selenium's own [public WebDriver test form](https://www.selenium.dev/selenium/web/web-form.html) in an isolated, short-lived GitHub Actions runner. This is NOT an arbitrary-site crawler, a customer-site test, permission to deploy, or original source reverse engineering.

The official [Selenium first-script tutorial](https://www.selenium.dev/documentation/webdriver/getting_started/first_script/) documents the `my-text` input, submit button, and `Received!` response. The form submits via GET, so the result URL may legitimately include a query: the existing rigid result-URL matcher was adjusted to require **exactly the expected HTTPS host/path** but tolerate a bounded nonsensitive query. The raw query or entered text is not saved to the review files.

## Implemented paths

- `scripts/public_capture_live_check.py`: no-argument **dry-run** has zero network/browser/writes. An **explicit** `--run` launches local Chrome, calls the existing `capture_fixed_flow()` for the published form, then calls the **actual** `register_captures()` and `verify_captures()` to check two redacted DOM-fact files. Reports 2/2 integrity only after validation. No raw HTML, cookies, network logs, credentials, or client data. Does **not** upgrade `inferred` provenance.
- `tests/test_public_capture_live_check.py`: five tests of a simulated fixed `ProbeResult`, use of actual capture-intake APIs, conservative authority flags, forged result fail-closed, CLI dry-run and `--run` opt-in. `tests/test_public_selenium_capture.py` adds a safe GET-result query regression (and refuses `access_token` query).
- `.github/workflows/p4-public-live-browser.yml`: runs on **this feature branch only** when the relevant paths change (or manually dispatched), with read-only contents permission and an 8-minute limit; installs Selenium/Pydantic/pytest; first runs three offline suites; then `xvfb-run -a python -m scripts.public_capture_live_check --run` on the public reference; if successful checks redacted evidence integrity and uploads `p4-selenium-public-evidence` (short 3-day retention) containing sanitized local files, intake manifest and report. No Vercel, no main changes, no customer DB/API, no repository secrets.

## What actually passed in this ChatGPT environment

The container retained a selected-file working copy `/mnt/data/astra_p4_integration`; every changed source/test/workflow Git blob was re-read from GitHub and matched the **exact locally tested** SHA.

```sh
python -m pytest -q tests/test_public_capture_live_check.py tests/test_public_capture_intake_chain.py tests/test_public_selenium_capture.py tests/test_owned_migration_schema.py tests/test_data_mapping.py
# 74 passed (0 fail, 0 skip): 5 new one-shot + 5 original-intake + 21 Selenium fake + 18 demo schema + 25 mapping.
python -m compileall -q astra_contracts scripts tests
# PASS
python -m scripts.public_capture_live_check
# dry_run; browser_started=false, network_used=false, files_written=false
```

Workflow YAML syntax was parsed independently. This is a **selected-file exact-original-code** local test, not complete branch regression.

## Remote status **not yet confirmed**

The new GitHub Actions workflow was committed to `feature/observation-contract-20261018`. However, connected GitHub commit status returned **zero statuses** and its run-list function exposes PR-triggered runs only; it cannot confirm this feature-branch **push** job's execution or result. **Do not call the live browser proof PASS until a job log and artifact show a successful public Chrome click plus 2/2 intake validation.** Workflow link:

`https://github.com/hibi89/astra_web_catcher/actions/workflows/p4-public-live-browser.yml`

Even if the runner is successful, its `original_site_behavior_verified`, `operator_origin_authenticated`, `semantics_independently_reviewed`, `generation_authorized`, and `deployment_authorized` flags remain **false** until a human independently reviews provenance and approves the narrow source behavior. GitHub runner execution is not a customer DB test.

## Remaining work and boundaries

1. Confirm exact GitHub Actions run and inspection of the uploaded, redacted artifact. If the runner is unavailable/fails, inspect the failure rather than treating lack of status as pass.
2. Independently review source URL, actual action, before/after state, captured at timestamps and hash consistency; do not silently upgrade `inferred`.
3. For real ASTRA implementation, obtain an approved user-owned schema and verify one **end-to-end** mapping/feature against disposable owned DB/API; not yet done.

Original protected `main` is unchanged, no source DB migration or production deployment, no customer credentials. `GenerationContract=blocked_pending_review`. Conservative overall roadmap progress **~49%** until live source evidence and real owner-data proof exist.
