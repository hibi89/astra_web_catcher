# ASTRA p4 — visible state vs interaction vs calculation evidence gate v0.1

This **offline, non-authorizing** stage prevents a screenshot or DOM excerpt from accidentally being promoted into proof of client/server behavior, an executed user action, or a calculation formula. It consumes an existing `ObservationBundle` and the **separate, temporary** capture intake directory, and rechecks captured files through `build_claim_review_packet()` before presenting any candidate for human review.

## Three independent assertion lanes per observation

| Layer | Eligibility | Output status | Interpretation |
| --- | --- | --- | --- |
| `visible_state` | At least one registered screenshot or sanitized DOM-text file | `visible_review_candidate_not_verified` | A human may compare **only displayed state/text**. No clicking, causality, formula or origin authenticated. |
| `interaction_transition` | Registered `manual_test` / `user_demonstration` evidence, a declared `action`, non-unknown original claim, and at least one **shared** state key that changed in `before`/`after` | `transition_review_candidate_not_verified` | A sequence is *reported* and may be inspected/replayed; no independent replay or verification has been performed. Screenshots alone cannot satisfy this lane. |
| `calculation_formula` | No automatic eligibility from captures, displayed percentages or interaction reports | `independent_formula_audit_required` | Formula/source specification, test inputs, expected outputs and independent review are needed in a **separate** authorization step. |

Missing evidence yields `missing_direct_visual_evidence` / `missing_recorded_interaction_sequence`. A candidate means "eligible for manual review", **never** that the behavior is confirmed. If the original claim is `unknown`, it cannot receive a visually/interaction-consistent opinion. An admitted label for a reviewer is **self-asserted**, not authenticated. Note outcomes are `needs_more_evidence` or `looks_consistent_but_not_verified`, and the latter requires eligible **linked** captures for only the visible or interaction layer. For a formula lane, only `needs_more_evidence` is permissible.

The source observation JSON, original claims, captures, manifests and customer apps remain unchanged. The CLI only prints JSON. All claims of original behavior/interaction/formula correctness, identity, production code generation, customer DB access and deployment remain explicitly false. This never substitutes for original-site browser testing.

## Reproducible synthetic case

```bash
OUT=$(mktemp -d /tmp/astra-capture-example-XXXXXXXX)
python -m astra_contracts.capture_intake register \
  fixtures/synthetic_capture_observation_20261018.json fixtures \
  fixtures/synthetic_capture_intake_request_20261018.json "$OUT"
python -m astra_contracts.evidence_claim_levels packet \
  fixtures/synthetic_capture_observation_20261018.json "$OUT"
# Notes require separately supplied version/packet_sha256/reviewer_claimed_label/notes JSON:
# python -m astra_contracts.evidence_claim_levels record OBSERVATION.json "$OUT" NOTES.json
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

The provided example is a fictional DOM fixture, **not real website evidence**. It yields six layer rows for two observations: the filter has one visible-review candidate but **no interaction/formula proof**, while the unknown calculation needs independent audit. An alternate test with a fictional manual-test file and matching before/after state yields only an interaction *candidate*, not verified causality.

## Test boundary / next task

On 2026-10-19 (KST), the focused local suite passed **349/349** (prior 325 + 24 new); `compileall` passed. Test coverage includes altered and stale capture files, unknown/missing visual evidence, manual-action prerequisites, unknown source claims, fabricated reviewer identity/approval flags, forged reviewer evidence, duplicate decisions, packet SHA mismatch and no writes. GitHub Actions and the previously blocked Chromium test were not attempted. **No real-world source capture was submitted.**

Next develop a **source-evidence-backed, intentionally small** test case that joins one permitted manual interaction trace → functional spec → independent synthetic behavior validation. Do not infer formulas, original backend design or user-owned schema permissions; keep `GenerationContract` blocked.
