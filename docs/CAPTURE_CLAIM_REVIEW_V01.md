# ASTRA p4 — Registered capture ⇄ observation claim review (v0.1)

## What this unit provides

An **offline, fail-closed, non-authorizing human triage packet** linking a previously registered manual capture with the source `ObservationBundle` claim IDs. It does not automatically interpret screenshot pixels, parse DOM for semantic facts, confirm original-site causality, retrieve sites, or alter the original observation's certainty. It does not impersonate an authenticated reviewer, grant user approval, or produce a customer implementation.

Inputs: (1) immutable source `ObservationBundle` v1 (2) a previously registered `astra-capture-*` temporary folder produced by `capture_intake.register_captures`. This tool reuses `capture_intake.verify_captures()` **before** constructing a packet; any missing, modified or unsafe file blocks review. It then binds each original observation to the IDs of its registered captures. An observation without a capture remains listed with no capture IDs, to make missing evidence visible. The original `ObservationBundle` is **not** changed.

## Reviewer opinions (separate explicit JSON)

- `more_evidence_needed` is available for any observation, even if no capture exists.
- `appears_consistent_with_visible_capture` is a *reviewer's unverified opinion*, never an automatic semantic fact. It requires at least one linked, byte-matching **screenshot or DOM text** ID and is disallowed for source observations whose certainty is `unknown`.
- `appears_inconsistent_with_visible_capture` also requires at least one linked screenshot or DOM text ID. A sanitized network trace, demonstration note or manual test cannot alone support a claim about **visible** screen contents.

The JSON submission requires the exact SHA-256 fingerprint of the current packet, an **unverified claimed reviewer label**, a nonempty rationale per opinion, and checked IDs from the observation's real registered capture list. Unknown observations/IDs, duplicate decisions, unlinked evidence, spoofed `verified`/`approved` flags, bad file paths and stale fingerprints fail. A reviewer opinion **never** changes the original claim's certainty. Original behavior, formulas, identity, capture authenticity and all authorization flags are enforced as `false`.

SHA-256 checks byte consistency, **not authenticity, original-site ownership or human consent**. The packet may contain manually supplied claim text; inspect and sanitize original source before use. The tool prints JSON to stdout only and never copies/exports raw screenshots, runs a browser, opens a network connection or modifies source data.

## Reproducible synthetic-only example

From repo root on a machine with the dependencies installed:

```bash
OUT=$(mktemp -d /tmp/astra-capture-demo-XXXXXXXX)
python -m astra_contracts.capture_intake register fixtures/synthetic_capture_observation_20261018.json fixtures fixtures/synthetic_capture_intake_request_20261018.json "$OUT"
python -m astra_contracts.capture_claim_review packet fixtures/synthetic_capture_observation_20261018.json "$OUT"
# To record a real manual opinion (not approval):
# python -m astra_contracts.capture_claim_review record OBSERVATION.json "$OUT" SUBMISSION.json
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

This sample is fabricated UI text, **not captured from a real website**. Its `example_filter` observation remains `inferred`, and its unknown formula remains `unknown`. A visible-consistency opinion must never be conflated with verified filter execution, formula correctness or permission to connect to a customer database.

## Validation and known constraints

Local Python 3.13: **325/325 pytest PASS** (302 previous + 23 new); `compileall` PASS, synthetic CLI register/packet/record read-only output successful. Existing httpx deprecation warning from an unrelated review UI test. No GitHub Actions or GUI Chromium reattempt, no actual new real screenshots, no independent human source inspection. Historical Japanese-nail claim still supported only by secondary archived notes. Code paths `astra_contracts/capture_claim_review.py`, `tests/test_capture_claim_review.py`.

## Subsequent step

After the operator explicitly supplies *real, authorized, sanitized* captures and a claim-specific manual review, build a verified and limited **UI-visible fact** protocol that distinguishes static appearance, user interactions, and opaque formulas. A visually consistent screenshot alone must not enable implementation or mark production readiness. The original fail-closed generation contract remains blocked.
