# ASTRA p4 — first public reference intake (2026-10-19)

## Public source

- Public page: https://www.selenium.dev/selenium/web/web-form.html — visible **Web form**, **Text input** and **Submit** in a read-only web text extraction.
- Publisher documentation: https://www.selenium.dev/documentation/webdriver/getting_started/first_script/ — example uses field `name=my-text`, Submit and checks the resulting `#message` text for `Received!`.

**Evidence categories are deliberately separate:** (1) public web text seen read-only, (2) an official publisher's explanation of expected behavior, and (3) a first-hand browser click and screenshot pair. Only (1) and (2) were gathered for this unit. The direct click/screenshot test **was not executed** in the environment; the presumed result URL was inaccessible through the read-only web tool. No administrator-blocked browser was bypassed.

Local human-curated excerpts: page SHA-256 `1bee345696adb474fb811365f993ee0327ef9f9e6fecfb1b3f94370c4f87a763`; official document excerpt SHA-256 `4a1cdf8a12978454e6321a4275bf51c0954611e9e2c09f8659ccb96648e55979`. These hashes pin **authored text excerpts**, NOT raw site HTML, screenshot origin, or site authenticity.

## Verified locally; transfer limitation

New offline source + fixed-URL, opt-in Selenium script + tests + excerpts + machine-readable report were created in the conversation working environment. **36/36 new tests pass** (35 before golden-record regression + one fixture check); **160/160 new-plus-related existing tests pass**; Python compileall passes. Collection of the larger suite shows 716 cases but the entire suite was **not** rerun. Existing production customer DB/API and protected generator unchanged.

The exact code and tests were exported to the current conversation file **`astra_p4_public_reference_probe_20261019.zip`**. These code/test bytes have **not** been pushed to GitHub in this unit because the GitHub connector could not directly ingest container-local source files. This GitHub commit records only the factual public-source triage and status; don't claim the repo test suite contains these new tests.

## Bounded continuation

When an authorized machine is available, run the fixed public Selenium demo script with an explicit opt-in; collect before/after PNGs and report. On browser block, stop without retrying. Import real screenshots through the existing capture-intake/transition-ledger machinery only after checking their origin and claims. Actual site equivalence, any owner's schema/DB access, mapping enablement, customer authorization, and deployment all remain **unverified / blocked_pending_review**. No automatic approval promotion.

## Transfer recovery addendum — 2026-10-19 KST

The earlier section "Verified locally; transfer limitation" records a *past* restriction and is **superseded for repository transfer status** by this addendum. The missing nine offline source, browser-plan, tests, documentation and fixture files were transferred as SHA-identical Git blobs and committed to the isolated feature branch as `57465a31f2837086d01050293d098007f8b4069d`. Each of these nine files was fetched again from GitHub and matched the locally tested blob hash. Public-reference tests **36/36 PASS**; Python compileall PASS. Additional preexisting suite test partitions were rerun in this follow-up and are recorded in HANDOFF/STATUS after completion; do not infer a full-suite result from this note alone.

**No elevation of evidence:** Source was a read-only third-party page text observation + publisher tutorial, not an actual live browser click or screenshot pair. The opt-in browser script defaults to dry-run, only targets the fixed Selenium demo URL, and **was not executed against the live site**. No source authenticity, site functional equivalence, owner DB authorization, deployment, or map enablement is claimed. `GenerationContract` remains `blocked_pending_review`. GitHub Actions and the previously blocked browser were not retried. Protected `main` remains unchanged.
