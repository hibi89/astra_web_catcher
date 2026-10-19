# ASTRA p4 — capture package → existing capture_intake integration checkpoint

Date: 2026-10-19 KST. Feature branch: `feature/observation-contract-20261018`. Purpose: validate the **real library boundary** between the preceding opt-in public Selenium local capture package and the already implemented `astra_contracts.capture_intake`. No original site click, customer DB, or deployment is claimed.

## Difference from prior work

Earlier `tests/test_public_selenium_capture.py` (20 passing tests) verified a fake WebDriver interaction and redacted local output shape. However, it did **not import** `capture_intake` or call its real `register_captures/verify_captures` functions. This unit adds `tests/test_public_capture_intake_chain.py` with **five** independent acceptance cases:

1. A synthetically constructed `ProbeResult` is converted using the **real** `make_review_package` into `bundle.json`, `request.json`, two redacted DOM-text files. Actual `ObservationBundle` and `CaptureIntakeRequest` Pydantic models parse the output. The **existing** `register_captures` copies both redacted text files to a fresh `astra-capture-*` OS-temp directory; **existing** `verify_captures` must return 2/2 `bytes_match_untrusted`. Original package bytes must remain unchanged. No verification flag may become true.
2. Tamper one stored file **without changing its length** and verify the real intake returns `evidence_incomplete` and `hash_mismatch`.
3. An altered observation bundle must fail at `stale` hash preflight before output.
4. A request referencing an unknown observation ID must fail before output.
5. Importing a forged manifest with `original_site_behavior_verified=true` must produce a Pydantic validation error.

The examples are **offline invented traces** used strictly to exercise integration mechanics; they are not first-hand Selenium source observations, nor user authentication or approved mappings.

## Bounded workflow/CI

Added `.github/workflows/p4-public-capture-chain.yml`, limited to changes in this integration test/its relevant code/the workflow on **only** `feature/observation-contract-20261018`. It checks out the full repository, installs Python 3.13 + minimal Pydantic/pytest requirements, and runs:

```sh
python -m pytest -q tests/test_public_capture_intake_chain.py tests/test_public_selenium_capture.py
python -m compileall -q astra_contracts scripts tests
```

Workflow permission: `contents: read`; max job duration 5 minutes; no browser, customer data, or external site interactions in the tests. No deployment stage.

**Verification honesty:** local selected-file workspace does **not** include the historical `capture_intake`/evidence-integrity module dependency tree. Therefore **these five new tests were not executed locally at document time**; their status is **pending full-checkout CI result**. GitHub's connected workflow lookup only returns PR-triggered runs; the push-triggered workflow result was not available through that lookup, and no commit status was returned. **Do not claim CI PASS from an absent status**, and do not claim 5/5 PASS until an actual run's exit status is confirmed.

## Already verified locally

```sh
python -m pytest -q tests/test_public_selenium_capture.py tests/test_owned_migration_schema.py tests/test_data_mapping.py
python -m compileall -q astra_contracts scripts tests
```

These selected existing test suites **63/63 PASS** and compileall PASS in the Python 3.13.5 isolated workspace. New test source was fetched back from GitHub and compared to committed bytes. This is not the entire historical 739+ suite.

## Next concrete acceptance

Check the p4 workflow/job results on GitHub (or execute the commands in a complete feature-branch checkout). If any of the five new cases fail, fix **the first real error**, rerun the new tests and prior 63, and update STATUS/HANDOFF. After true capture→intake integration is validated, collect **one actual** permitted reference-site before/after from an operator-owned browser and independently review provenance. Do not promote `inferred` into `observed` automatically. Owner DB/API, protected `main`, Vercel, application migrations, and confidential data remain untouched.

`GenerationContract=blocked_pending_review`. Conservative overall roadmap estimate **~49% unchanged**, since no first-hand source behavior or customer-owned integration has yet been demonstrated.
