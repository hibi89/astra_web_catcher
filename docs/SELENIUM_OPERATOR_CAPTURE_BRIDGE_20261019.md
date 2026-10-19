# ASTRA p4 — opt-in local Selenium public form capture bridge (2026-10-19)

## Why this unit matters

Earlier ASTRA work could register, hash, compare and review **operator-supplied** before/after evidence, but lacked a way to acquire an actual source interaction. The connected Chat browser is read-only; previous container Chromium automation was blocked. This unit introduces **one explicitly opt-in, locally executable, fixed-target Selenium WebDriver capture command** to close that acquisition gap **when a compatible user-controlled Chrome environment is available**. It does not circumvent blocked browser controls or request third-party private access.

Publisher's Selenium [First Script tutorial](https://www.selenium.dev/documentation/webdriver/getting_started/first_script/) publicly documents entering text into `my-text`, clicking `button` and reading `#message`; the published result is `Received!`. The three public pages were **read-only rechecked** on 2026-10-19. Reading those pages **did not** constitute a live click.

## Design and operational contract

Two options considered:

- Repeat previously blocked local Chrome automation in the current container — expected to waste time and fail again; **not attempted**.
- Ship a **fixed-public-reference local operator probe** as a separate command with testable fake WebDriver and output that reuses existing intake; **selected**. No paid model/API calls, source-site cloning, or DB connectivity. Selenium and Chrome must be installed on the operator machine for its explicit live command.

Source: `scripts/public_selenium_capture.py`.

The CLI **defaults to dry-run** with no browser, network, files or credentials. `--run` intentionally launches a local visible Chrome WebDriver, visits only `https://www.selenium.dev/selenium/web/web-form.html`, enters a **fixed nonsensitive** demo value, clicks its published Submit button, waits for `#message == Received!`, and rejects all unexpected final origins, redirects, query strings or results. On failure, no evidence package is generated.

On a successful operator run it creates a **fresh** OS-temp `astra-selenium-public-*` folder containing:

| File | Purpose |
| --- | --- |
| `evidence/before.txt` | fixed URL, `my-text` control and no result text |
| `evidence/after.txt` | published result URL, `#message` and `Received!` only |
| `bundle.json` | actual `ObservationBundle` Pydantic v1; **certainty remains inferred** until independent review |
| `request.json` | proposed two-file `CaptureIntakeRequest` v0.1 input with matching canonical bundle fingerprint |
| `run_metadata.json` | explicit unreviewed provenance and **all authority flags false** |

It never writes raw page HTML, screenshots, submitted text, cookies, credentials, network headers, traces or customer rows. This deliberately limits evidence richness; reviewers can inspect the operator-supplied minimal DOM fact claims, not assume screenshots or implementation details were verified. No activity occurs on real customer sites; the public URL is hardcoded.

## Windows PowerShell procedure (operator's own Chrome)

From the **feature branch checkout** on an environment with Python, installed Chrome and network access to selenium.dev:

```powershell
py -m pip install selenium
py -m scripts.public_selenium_capture
py -m scripts.public_selenium_capture --run
```

The successful `--run` response contains an `output_root` in the user's OS temp directory. Keep this path local and examine the five sanitized files before accepting them.

To submit the two operator-produced text files to the **existing, previously implemented** ASTRA capture-intake contract, from repository root:

```powershell
$runRoot = '<exact output_root printed by --run>'
$out = Join-Path $env:TEMP ('astra-capture-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
py -m astra_contracts.capture_intake register "$runRoot\bundle.json" "$runRoot" "$runRoot\request.json" "$out"
py -m astra_contracts.capture_intake verify "$runRoot\bundle.json" "$out"
```

The intake CLI verifies *local bytes*, not authenticated capture origin or live-site semantics. The manually supplied local file label does not confer proof of an operator's identity. The `ObservationBundle` remains unapproved; `CaptureIntake` records `pending_manual_evidence_review` and does **not** upgrade `inferred` to `observed` or grant generation/mapping/deploy access. The bridge→intake command sequence **was not run against real WebDriver output in this container**; test it locally before treating it as an end-to-end pass.

## Actual verification, not asserted capabilities

On Python 3.13.5 in a selected-file workspace:

```sh
python -m pytest -q tests/test_public_selenium_capture.py tests/test_owned_migration_schema.py tests/test_data_mapping.py
python -m compileall -q astra_contracts scripts tests
python -m scripts.public_selenium_capture
```

**63/63 PASS**: 20 new fake-WebDriver and output contract tests plus 18 existing owned migration tests and 25 existing data-mapping tests; 0 FAIL, 0 SKIP. Dry-run CLI PASS and compileall PASS. Source/test were written to feature branch and GitHub Git blob SHA re-read matched the tested local files **2/2**. The fake driver suite checks exact allowlisted original/result URLs, rejected redirect and changed output, fixed test input, redacted capture JSON, Pydantic-compatible bundle, canonical fingerprint, missing approvals, and no unsafe overwrites.

**Not done**: real Chrome/WebDriver startup, Selenium site's actual click, first-hand screenshot, production app, entire earlier 739+ tests, full Git checkout, user DB/API, deployment, or confirmed downstream intake with real browser-produced files. These remain independent blockers. Installing Selenium on the end-user's PC and running `--run` may download needed driver binaries via Selenium Manager and uses the PC's network, and is **optional**.

## Next bounded work

When a compatible local Chrome machine is available, run **one** public Selenium test and review/verify its local capture. Do not automatically upgrade review status. Then test the two-input intake→transition ledger on the **captured** files, manually review provenance/semantics and only afterward consider a controlled mapping proof to a disposable owner-owned schema. No original DB, main, credentials or deployment should be changed without separately granted approval.

**Conservative overall milestone estimate remains ~49%** until real observation and end-to-end acceptance replace publisher-documentation-only demonstrations.
