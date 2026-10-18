# ASTRA p4 — before/after capture provenance ledger v0.1

## Delivered

`astra_contracts.capture_transition_ledger` is an **offline, review-only ledger** for a manually supplied *pair* of UI snapshots. It reuses the existing `capture_intake` byte-integrity and original `ObservationBundle` checks. It neither opens a website nor authenticates a screenshot. **No claim of original-site equivalence, customer permission, generation authorization, or database access is made.**

## Operator procedure for an independently authorized reference site

1. Verify the site is yours or that you have permission to inspect the permitted pages. Do not bypass access controls or run blocked browser automation.
2. Define **one** narrow user interaction, e.g. selecting a filter. Record the exact local time *with timezone*, URL without secret tokens, expected target field, and a plain description of the action. Avoid raw session information, keys, PII and any protected/private UI.
3. Capture a **before** screenshot or minimal sanitized DOM text, perform only that interaction, capture the corresponding **after** artifact. Prefer the *same* representation type for both. Note that screenshots and claimed timestamps can be fabricated; this tool only checks structure and bytes.
4. Update the **original observation bundle** separately with explicitly identified `before` / `after` scalar state, its action description and an appropriate certainty, without silently changing `inferred`/`unknown` to `observed`. Keep real observation provenance separate from fictional examples.
5. Use the existing `CaptureIntakeRequest` with `source_kind=manually_supplied_local_files` and two captures linked to the same observation ID. Register into an **empty** `astra-capture-*` directory directly under system temp: 

   `python -m astra_contracts.capture_intake register <bundle.json> <source_root> <request.json> <empty_temp_dir>`

6. Create a `TransitionPlan` with original bundle and returned intake-manifest fingerprints, a unique transition ID, both capture IDs, changed field name, and the exact action text. Execute:

   `python -m astra_contracts.capture_transition_ledger <bundle.json> <intake_dir> <plan.json>`

7. Review `findings[].status`. `paired_bytes_present_unverified` means **only** both supplied files match their registered hashes, timestamps and claimed field delta are structurally consistent. It **does not** mean the original site was visited, screenshot content corresponds to UI state, user identity was checked, or the interaction semantics are approved.
8. Have a human independently examine provenance and both snapshots. Human review is a **separate** workflow. No result of this v0.1 ledger enables controls, authorizes code/deploy, validates calculations or links to owner DB.

## Fail-closed rules

- Check all intake file bytes again; reject missing, altered or symlinked files, a forged/tampered manifest and wrong bundle fingerprint.
- Reject unknown observation IDs, unknown/unlinked capture IDs, duplicate transition IDs/pairs, reusing the same file for both sides, unsupported media (archive/manual prose), secret-looking evidence paths, forged flags and stale fingerprints.
- Missing action, absent/mismatched state type, unchanged state, backwards capture times, or incompatible snapshot kinds produce **review-only findings**, not an enabled UI.
- The output contains immutable **False** flags for `original_site_behavior_verified`, `screenshot_meaning_checked`, `reviewer_identity_verified`, `ui_controls_enabled`, `code_generation_authorized`, `owner_database_access_authorized`, `deployment_authorized`.

## Reproducible fictional fixture

`fixtures/synthetic_transition_pair_*_20261019.json` and corresponding `fixtures/evidence/synthetic_transition_*_20261019.txt` are deliberately made-up data, **not evidence from any website**. Tests register the fixture pair in temp, execute the same CLI path, then assert review-only output. They must never be relabeled as real capture evidence.

## Next integration boundary

A human-accessible source capture workflow and independent visual/source validation are still not implemented. The mapped preview remains disabled; no attempt is made to upgrade the archived observation or connect customer DB/API. The original protected synthetic generator, production data, GitHub Actions and blocked browser tooling are unchanged.
