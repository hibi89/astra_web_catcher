# ASTRA — Evidence & Field Meaning Review Decision Record v0.1

**Scope:** One offline reviewer-opinion record unit. It turns a validated `FunctionalSpecDraft`, an *explicitly declared* DB/API schema, and an independently recomputed `MappingReport` into a structured human-review packet. A reviewer may separately supply responses, but **no statement in either artifact verifies identity, establishes actual original website behavior, approves a mapping, or grants access to any DB/API, code generation, source modification, or deployment**.

## Why this design

- **Alternative A — allow a review checkbox to authorize code generation:** rejected. A checkbox or an unverified name is not permission to change a user's original system, and earlier `GenerationContract` explicitly remains `blocked_pending_review`.
- **Alternative B — record opinions on immutable input fingerprints, independently from permissions:** selected. The user can identify disputed evidence, missing formulas and mapping semantics without changing any source data.

## Files and behavior

- `astra_contracts/reviewer_decisions.py`: deterministic `packet` and `record` CLI modes. JSON **stdout only**; never writes a project file.
- `fixtures/synthetic_review_packet_20261018.json`: machine-readable example produced from archived Japanese nail UI observations plus an **invented, explicitly synthetic DB schema**. It includes **13 review items: 1 archived observed behavior, 2 unresolved behavior claims, and 10 field-semantics/mapping items**. No original screenshots were retrieved. The 3 structurally compatible fields are not semantically verified.
- `tests/test_reviewer_decisions.py`: 23 regression tests covering stable hashes, stale-source detection, mapping report tampering, archived evidence limitations, missing references, duplicate responses, forged permission status, and CLI read-only behavior.

`ReviewPacket` fingerprints the three validated inputs using canonical JSON hashes and records each item's category, claim/mapping mismatch, original evidence references where available, and archive-only status. A valid packet has `status=pending_human_review` and all authorization flags fixed false. It **does not assign a reviewer**.

`ReviewSubmission` is a separately authored JSON with fields `version`, `packet_sha256`, `reviewer_claimed_label`, and a nonempty `responses` array. Each response contains `item_id`, one of `supported_as_proposal`, `needs_more_evidence`, `rejected_for_target`, a rationale, and an optional list of *already referenced* evidence paths claimed to have been checked. Reviewer labels are **unverified claims**. A submission based on a stale packet or an unknown review item is rejected. Archived text alone cannot justify `supported_as_proposal` for original browser behavior. Unresolved behavior or incompatible/unmapped source fields cannot be marked supported as proposals.

The resulting `ReviewRecord` lists unsubmitted items as `pending` and supplied responses as `recorded_opinion`. Even if all 13 items receive recorded opinions, `reviewer_identity_verified`, `reference_behavior_verified`, `field_meanings_verified`, `schema_verified_live`, `user_approval_verified`, `code_generation_authorized`, `database_access_authorized`, `source_changes_authorized`, and `deployment_authorized` remain **false**. This record is an auditable *discussion input*, never an electronic signature or actual authorization.

## Commands from repository root

```bash
python -m astra_contracts.reviewer_decisions packet \
  fixtures/jp_nail_functional_spec_draft_20261018.json \
  fixtures/synthetic_owned_schema_mapping_20261018.json \
  fixtures/synthetic_mapping_report_20261018.json

# To record a user-created opinion submission, supply an existing reviewed JSON
# as the fourth positional path. Do NOT treat this as real DB/change consent.
python -m astra_contracts.reviewer_decisions record \
  fixtures/jp_nail_functional_spec_draft_20261018.json \
  fixtures/synthetic_owned_schema_mapping_20261018.json \
  fixtures/synthetic_mapping_report_20261018.json \
  /path/to/sanitized-human-review-submission.json

python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py \
  tests/test_functional_spec.py tests/test_data_mapping.py tests/test_generation_contract.py \
  tests/test_synthetic_generator.py tests/test_synthetic_bridge.py \
  tests/test_synthetic_acceptance.py tests/test_reviewer_decisions.py
python -m compileall -q astra_contracts tests
```

Verified locally, 2026-10-18 KST: **193/193 pytest PASS** (previous 170 + 23 new), CLI packet JSON roundtrip PASS, `compileall` PASS. Actual production auth, customer DB schema verification, graphical browser E2E, and real owner permission were **not** tested; none is claimed. Original `main`, `/shop`, `/jobs`, and research/experiment apps and DBs remain untouched. This file belongs only on the isolated ASTRA feature branch.

**Next single unit:** add a human review UI or import/export validation for this *unverified opinion workflow*, or introduce a **separate, explicitly authenticated approval protocol** only after defining the user's preferred authorization model. Do not use opinions as authorization or silently promote them to `generation_contract` approval.
