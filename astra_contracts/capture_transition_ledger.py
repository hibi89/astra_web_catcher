"""Offline before/after evidence-pair ledger; structural review, never site verification.

CLI: python -m astra_contracts.capture_transition_ledger BUNDLE.json INTAKE_DIR PLAN.json
No network, browser, customer DB, changes to original observation, or authorization.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.capture_claim_review import build_claim_review_packet
from astra_contracts.capture_intake import MANIFEST_NAME, CaptureIntakeManifest, _checked_folder
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Certainty, EvidenceKind, ID_PATTERN, ObservationBundle

HEX64 = r'^[0-9a-f]{64}$'
SNAPSHOTS = {EvidenceKind.SCREENSHOT, EvidenceKind.DOM_TEXT}


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TransitionProposal(ClosedModel):
    id: str = Field(pattern=ID_PATTERN)
    observation_id: str = Field(pattern=ID_PATTERN)
    before_capture_id: str = Field(pattern=ID_PATTERN)
    after_capture_id: str = Field(pattern=ID_PATTERN)
    changed_field: str = Field(min_length=1, max_length=100)
    operator_action: str = Field(min_length=1, max_length=250)

    @model_validator(mode='after')
    def distinct_snapshots(self):
        if self.before_capture_id == self.after_capture_id:
            raise ValueError('before and after capture must be distinct')
        return self


class TransitionPlan(ClosedModel):
    version: Literal['0.1'] = '0.1'
    source_kind: Literal['untrusted_local_operator_capture_pair'] = 'untrusted_local_operator_capture_pair'
    original_bundle_sha256: str = Field(pattern=HEX64)
    intake_manifest_sha256: str = Field(pattern=HEX64)
    proposals: list[TransitionProposal] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_proposals(self):
        ids = [p.id for p in self.proposals]
        pairs = [(p.observation_id, p.before_capture_id, p.after_capture_id, p.changed_field)
                 for p in self.proposals]
        if len(ids) != len(set(ids)) or len(pairs) != len(set(pairs)):
            raise ValueError('duplicate transition proposal or evidence pair')
        return self


class TransitionFinding(ClosedModel):
    transition_id: str
    observation_id: str
    status: Literal[
        'paired_bytes_present_unverified',
        'source_claim_unconfirmed',
        'missing_or_mismatched_action',
        'missing_comparable_before_after',
        'unchanged_claimed_field',
        'capture_order_invalid',
        'incomparable_capture_kinds',
    ]
    before_capture_id: str
    after_capture_id: str
    changed_field: str
    before_value: str | int | float | bool | None = None
    after_value: str | int | float | bool | None = None
    explanation: str
    allowed_to_enable_ui: Literal[False] = False


class TransitionLedger(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['evidence_pair_triage_only'] = 'evidence_pair_triage_only'
    original_bundle_sha256: str
    intake_manifest_sha256: str
    plan_sha256: str
    byte_integrity_checked: Literal[True] = True
    operator_origin_authenticated: Literal[False] = False
    screenshot_meaning_checked: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    semantic_approval_granted: Literal[False] = False
    ui_controls_enabled: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    owner_database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    findings: list[TransitionFinding] = Field(min_length=1)
    human_review_required: Literal[True] = True


def build_transition_ledger(bundle: ObservationBundle, intake_dir: Path,
                            plan: TransitionPlan) -> TransitionLedger:
    """Hash-bind a proposal to an intact local intake, without inferring screen semantics."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    plan = TransitionPlan.model_validate(plan.model_dump(mode='json'))
    # build_claim_review_packet verifies all registered bytes and every linkage.
    packet = build_claim_review_packet(bundle, intake_dir)
    if plan.original_bundle_sha256 != fingerprint(bundle):
        raise ValueError('stale original observation bundle SHA-256')
    if plan.intake_manifest_sha256 != packet.intake_manifest_sha256:
        raise ValueError('stale intake manifest SHA-256')
    folder = _checked_folder(Path(intake_dir))
    manifest_path = folder / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('unsafe intake manifest')
    manifest = CaptureIntakeManifest.model_validate_json(manifest_path.read_text(encoding='utf-8'))
    if fingerprint(manifest) != packet.intake_manifest_sha256:
        raise ValueError('intake changed during validation')
    capture_by_id = {x.evidence.id: x for x in manifest.entries}
    observation_by_id = {x.id: x for x in bundle.observations}
    findings = []
    for proposal in plan.proposals:
        if proposal.observation_id not in observation_by_id:
            raise ValueError(f'unknown observation: {proposal.observation_id}')
        if proposal.before_capture_id not in capture_by_id or proposal.after_capture_id not in capture_by_id:
            raise ValueError(f'unknown before/after capture: {proposal.id}')
        before = capture_by_id[proposal.before_capture_id]
        after = capture_by_id[proposal.after_capture_id]
        if (proposal.observation_id not in before.proposal_observation_ids or
                proposal.observation_id not in after.proposal_observation_ids):
            raise ValueError('both captures must be linked to the same observation in intake')
        if before.evidence.kind not in SNAPSHOTS or after.evidence.kind not in SNAPSHOTS:
            raise ValueError('before/after require screenshot or DOM text snapshots')
        ob = observation_by_id[proposal.observation_id]
        before_val = ob.before.get(proposal.changed_field)
        after_val = ob.after.get(proposal.changed_field)
        if ob.certainty is not Certainty.OBSERVED:
            status, explanation = 'source_claim_unconfirmed', 'Source certainty is not observed; attached files do not promote it.'
        elif ob.action is None or ob.action.strip() != proposal.operator_action.strip():
            status, explanation = 'missing_or_mismatched_action', 'Action is not explicitly recorded consistently in the original bundle.'
        elif (proposal.changed_field not in ob.before or proposal.changed_field not in ob.after or
              type(before_val) is not type(after_val)):
            status, explanation = 'missing_comparable_before_after', 'Same typed field is required in both claimed states.'
        elif before_val == after_val:
            status, explanation = 'unchanged_claimed_field', 'Claimed before/after state does not change.'
        elif before.evidence.captured_at >= after.evidence.captured_at:
            status, explanation = 'capture_order_invalid', 'Before capture must have a strictly earlier timestamp.'
        elif before.evidence.kind != after.evidence.kind:
            status, explanation = 'incomparable_capture_kinds', 'Pair needs comparable snapshot types.'
        else:
            status, explanation = ('paired_bytes_present_unverified',
                                    'Two operator-supplied file hashes and claimed state delta align structurally; content and origin unverified.')
        findings.append(TransitionFinding(
            transition_id=proposal.id, observation_id=proposal.observation_id,
            before_capture_id=proposal.before_capture_id, after_capture_id=proposal.after_capture_id,
            changed_field=proposal.changed_field, before_value=before_val,
            after_value=after_val, status=status, explanation=explanation,
        ))
    return TransitionLedger(original_bundle_sha256=fingerprint(bundle),
                            intake_manifest_sha256=packet.intake_manifest_sha256,
                            plan_sha256=fingerprint(plan), findings=findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline, unverified before/after capture ledger')
    parser.add_argument('observation_file', type=Path)
    parser.add_argument('intake_dir', type=Path)
    parser.add_argument('plan_file', type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation_file.read_text(encoding='utf-8'))
        plan = TransitionPlan.model_validate_json(args.plan_file.read_text(encoding='utf-8'))
        ledger = build_transition_ledger(bundle, args.intake_dir, plan)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(ledger.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
