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


## 2026-10-19 follow-up — original GitHub-source local integration PASS

The prior "5 new tests not executed locally" wording above describes the **earlier checkpoint** and is now superseded by this tested follow-up.

**Method:** Direct `git clone` was unavailable because GitHub DNS resolution failed in the container. Restored the originally committed, byte-for-byte Python modules `capture_intake.py`, `evidence_integrity.py` and `generation_contract.py` alongside the existing Pydantic, functional-spec, observation and test files into a selected-file local workspace. Verified **16/16 Git blob SHA1 identifiers** against the exact feature-branch source/test/fixture blobs; including `capture_intake=5e9da4c676c3cb590870c69fd66bdaa6faf0823d`, `evidence_integrity=54d204776a10158225052b3e4ca98a2810336b10`, `generation_contract=7def1a4db497bcc1cc18cbff1134ea02c12fa0f5`, and new test `test_public_capture_intake_chain=3cc8922bcc352a6c2e2d4dc9b3645d1c5762a53f`.

**Executed commands** (Python 3.13.5, container local OS temp):

```sh
python -m pytest -q tests/test_public_capture_intake_chain.py tests/test_public_selenium_capture.py tests/test_owned_migration_schema.py tests/test_data_mapping.py
# 68 passed in 1.01s; 5 new +20 Selenium fake +18 schema +25 mapping
python -m compileall -q astra_contracts scripts tests
# PASS
python -m scripts.public_selenium_capture
# dry_run / browser_started=false / network_used=false / files_written=false
```

**Result:** **68/68 PASS, 0 FAIL, 0 SKIP**, on original GitHub byte-identical source files, with the **actual existing** `capture_intake` implementation, no stubs/mocks for its library functions. The successful register/verify path produced 2/2 matching `bytes_match_untrusted` evidence entries. Failing cases rejected tampered same-length bytes, stale observation fingerprint, bad observation association, and forged approval flags. These represent **synthetic prebuilt ProbeResult cases**, not actual live website behavior. The previous "5 tests PENDING" condition is **now closed for local execution**, while GitHub Actions status remains **independently unconfirmed** (connected GitHub commit status returned none, PR-workflow lookup excludes push runs).

**Boundaries still outstanding:** No complete repository checkout or full 739+ test suite, no original-site Chrome click, no source screenshot provenance, no real owner DB/API, no GitHub Actions green check, no Vercel deployment. `GenerationContract=blocked_pending_review`. Feature branch changes in this follow-up are **documentation only**, no source alterations; main remains protected. Roadmap progress stays conservatively **~49%**.
