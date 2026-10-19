# p4 ASTRA — full repository regression and four browser engines (2026-10-19)

## Actual result and provenance

The **second** GitHub Actions run [39220632083](https://github.com/hibi89/astra_web_catcher/actions/runs/39220632083) finished **completed/success** on feature/observation-contract-20261018 at tested code/workflow commit `645a77a4264f802479e3cdd0a9e5bc656df78f59`. All three jobs completed successfully. These are observed GitHub CI results, not inferred from authored tests.

| Job (actual OS/engine) | Result | Evidence artifact |
| --- | --- | --- |
| Full repository pytest, Ubuntu Python 3.13.16 | **894 passed, 2 skipped, 2 warnings in 91.08 seconds; 0 failed** | [12171502726](https://github.com/hibi89/astra_web_catcher/actions/runs/39220632083/artifacts/12171502726) |
| Linux Playwright Chromium 156.0.8078.4, Firefox 157.0, WebKit 27.2 | **12/12 browser checks PASS**, each engine 3 viewports + 1 injection probe | [12171656865](https://github.com/hibi89/astra_web_catcher/actions/runs/39220632083/artifacts/12171656865) |
| Real Microsoft Edge 155.0.4283.62 on windows-latest | **4/4 browser checks PASS**, 3 viewports + 1 injection probe | [12171726821](https://github.com/hibi89/astra_web_catcher/actions/runs/39220632083/artifacts/12171726821) |

GitHub Actions workflow: `.github/workflows/p4-regression-cross-engines.yml`. Reusable browser script: `scripts/p4_multi_browser_smoke.py`, Git blob SHA `2507394d81583e564fef11be9a75f166c525d390`; this byte-identical source previously ran locally under Chromium using both the genuine pinned OWID ZIP and the synthetic-only configuration, 4/4 per invocation. CI is a fresh checkout of the feature branch.

## What the browser suite actually checks

All engines load the deterministic **synthetic** chart/table preview through Playwright `page.set_content`. The checks run at desktop 1366×768, mobile 390×844 and small mobile 320×640. For each context they check 15 SVG points, 15 table rows, correct initial mode, click Chart→Table, Enter→Chart, Space→Table, visible/hidden states, `aria-pressed`, horizontal overflow and no page-level JavaScript exceptions or network requests. One synthetic hostile HTML `onerror` payload per engine remains escaped and does not execute. This is an active browser test but **not** direct `file://` navigation, actual hardware phones, accessibility certification, all XSS variants, macOS Safari or production integration.

### The two real CI skips

Both skips are explicit tests that need the retained 274126-byte historical OWID browser screenshot ZIP:

- `tests/test_chart_table_synthetic_bridge.py:38` — original pinned GitHub Actions ZIP unavailable inside CI
- `tests/test_synthetic_chart_table_preview.py:126` — no pinned OWID evidence ZIP provided; no substitute constructed

The exact ZIP `6ad5f561b78271be7da3b4efb8e61fcc1a6c269b4ebf8a26e1b32c23b81717e6` was independently validated and used with bridge/preview earlier in the **local environment**. These two CI skips are **not** described as passed. Full regression cannot be claimed 896/896.

## Troubleshooting chronology

1. First CI attempt [39220393619](https://github.com/hibi89/astra_web_catcher/actions/runs/39220393619) was interrupted by **HTTP 401** on a redirect while trying to download an older GitHub Actions artifact ZIP. The suite itself had not failed; the prerequisite did.
2. No repeat of the same blocked download. The proof ZIP is optional for browser presentation and retains its separate local provenance. Changed the reusable smoke script's `--archive` to optional; added explicit `pinned_archive_verified` flag. Verified locally that both genuine-pinned and synthetic-only Chromium paths pass, 4/4 each.
3. Removed the protected artifact download from CI; kept tests fail-closed and transparently reported two evidence-dependent skips. Retried with second run above, 3/3 jobs SUCCESS. No unapproved source semantic inference or customer DB/API.

## Reproduction

From repo root with Python 3.11+:

```bash
python -m pip install -r requirements.txt 'selenium>=4.27,<5'
python -m pytest -q -ra tests
python -m playwright install --with-deps chromium firefox webkit
python -m scripts.p4_multi_browser_smoke --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --engine chromium --engine firefox --engine webkit
```

Windows Edge requires actual Windows and Playwright-installed Edge:

```powershell
python -m playwright install msedge
python -m scripts.p4_multi_browser_smoke --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --engine msedge
```

Passing `--archive <exact-pinned-zip-path>` additionally validates provenance; no archive is needed to test only the synthetic HTML renderer. Browser results in JSON are preserved by the CI workflow for seven days.

## Scope and safety

- No owner-owned schema, customer API, production database, credentials, deployed app, or main-branch merge touched.
- Public OWID page's internal code/formulas and equivalent semantic correctness **not verified**; the present preview uses **invented sample measurements** and no external page data.
- Four synthetic mappings are only structurally compatible; **approval FALSE**, `GenerationContract=blocked_pending_review`, database/generation/deployment authorization FALSE.
- Work is limited to full Python regression of the feature checkout and four desktop browser engines rendering synthetic data. It does **not** prove general reference-URL→app synthesis, production reliability or customer integration.
- Estimated overall ASTRA completion remains conservatively **~49%** as a subjective roadmap indicator; passing a larger test suite does not automatically make the unfinished product complete.

**Next unit:** choose a narrow functional integration of synthetic chart/table with owner-controlled disposable backend/schema, or inspect and plan a documented authorized source/schema handoff. Preserve main and approvals.
