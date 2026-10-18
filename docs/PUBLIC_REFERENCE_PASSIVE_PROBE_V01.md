# ASTRA p4 — First real public-reference probe, passive-only v0.1

## What was independently retrieved

On 2026-10-19 KST, read-only public web text was retrieved from the **official Selenium Web form example** at:

- https://www.selenium.dev/selenium/web/web-form.html — web ref `turn461840view0`; visible `Web form`, `Text input` and `Submit` in the extracted page text.
- https://www.selenium.dev/documentation/webdriver/getting_started/first_script/ — web ref `turn461840view2`; publisher's example describes locating `name=my-text`, typing into the public demo, pressing its submit button and checking `Received!` via the resulting `#message` element.

The above source excerpts are **abbreviated, human-curated records of web-tool text**, not authentic HTML files, original DOM snapshots, browser screenshots, or cryptographically signed web responses. Their SHA-256 values prove only integrity of the local excerpts. The publisher's example describes **expected behavior**, not a browser click executed by ASTRA. An attempted read-only open of the presumed result page was *not accessible*; no browser interaction was performed. No original-site behavior verification, code generation authorization, UI mapping enablement, owner DB access or deployment is asserted.

## Reproducible local passive check (no network)

```bash
python -m astra_contracts.public_reference_probe \
  fixtures/public_selenium_form_note_20261019.json \
  fixtures/public_selenium_form_page_excerpt_20261019.txt \
  fixtures/public_selenium_official_docs_excerpt_20261019.txt
```

The report returns `public_page_readonly_and_publisher_documented_only`, immutable false provenance/permission flags, and the unchanged SHA-256 hashes of both authored excerpt files. All invalid, stale or altered excerpts fail closed. This is not a screenshot comparison.

## Explicitly gated independent browser smoke script

The separately authored script `scripts/selenium_public_form_capture.py` is **dry-run by default**. It never accepts an arbitrary target URL and never logs in. To actually perform the official site's fixed public demo interaction on a machine where Selenium/Chrome and internet access are authorized, an operator must deliberately use `--run-public-demo`. Only then, the script opens the one fixed public demo, fills fictional static text into `my-text`, clicks the publicly documented Submit button, checks `Received!`, and stores SHA-256-pinned screenshots plus a report in a new local temp directory. It does not use this project's blocked browser environment and does not bypass administrator policies. On any error, the script quits without automatic retry. Even a successful screenshot pair is **not** an automatic grant to map original-site functions or use a customer database.

No one is required to run the opt-in browser smoke to validate this bounded development unit. Its injected fake-driver unit tests do not count as site verification.

## Next bound

If actual captured screenshots and provenance from an authorized run become available, import the evidence through the *existing* capture intake and transition ledger. Human review of real before/after meaning is still necessary before mapping a control. Otherwise retain status unverified and move to unrelated, accessible public references.
