"""ASTRA p4: offline three-lane evidence review, NEVER behavior/formula proof.

Visible screenshot state, user-reported interaction sequence, and derived formula
are different assertions. This module does NOT infer a website's implementation
or upgrade observation certainty, inspect remote pages, connect DB, or approve code.

    python -m astra_contracts.evidence_claim_levels packet OBSERVATION.json INTAKE_DIR
    python -m astra_contracts.evidence_claim_levels record OBSERVATION.json INTAKE_DIR NOTES.json
"""
from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.capture_claim_review import build_claim_review_packet
from astra_contracts.capture_intake import MANIFEST_NAME, CaptureIntakeManifest, _checked_folder
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Certainty, EvidenceKind, ObservationBundle


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AssertionLayer(str, Enum):
    VISIBLE_STATE = 'visible_state'
    INTERACTION_TRANSITION = 'interaction_transition'
    CALCULATION_FORMULA = 'calculation_formula'


class GateState(str, Enum):
    MISSING_DIRECT_VISUAL_EVIDENCE = 'missing_direct_visual_evidence'
    VISIBLE_REVIEW_CANDIDATE = 'visible_review_candidate_not_verified'
    MISSING_RECORDED_SEQUENCE = 'missing_recorded_interaction_sequence'
    TRANSITION_REVIEW_CANDIDATE = 'transition_review_candidate_not_verified'
    FORMULA_AUDIT_REQUIRED = 'independent_formula_audit_required'


class LayerItem(ClosedModel):
    observation_id: str
    layer: AssertionLayer
    evidence_ids: list[str]
    status: GateState
    prerequisite_notes: list[str]
    original_claim_certainty: Certainty
    visually_verified: Literal[False] = False
    interaction_verified: Literal[False] = False
    formula_verified: Literal[False] = False


class ClaimLevelPacket(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['human_review_queue_only'] = 'human_review_queue_only'
    source_observation_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    capture_manifest_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    items: list[LayerItem] = Field(min_length=3, max_length=1500)
    original_behavior_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    identity_verified: Literal[False] = False
    user_approval_verified: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False

    @model_validator(mode='after')
    def unique_layers(self):
        keys = [(i.observation_id, i.layer) for i in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate assertion layer')
        return self


class ReviewerLayerNote(ClosedModel):
    observation_id: str
    layer: AssertionLayer
    outcome: Literal['needs_more_evidence', 'looks_consistent_but_not_verified']
    evidence_ids_checked: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(min_length=8, max_length=1200)

    @model_validator(mode='after')
    def unique_evidence(self):
        if len(self.evidence_ids_checked) != len(set(self.evidence_ids_checked)):
            raise ValueError('duplicate checked evidence IDs')
        return self


class LayerSubmission(ClosedModel):
    version: Literal['0.1']
    packet_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer_claimed_label: str = Field(min_length=2, max_length=100)
    notes: list[ReviewerLayerNote] = Field(min_length=1, max_length=1500)

    @model_validator(mode='after')
    def unique_notes(self):
        keys = [(n.observation_id, n.layer) for n in self.notes]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate reviewer note for an assertion layer')
        return self


class LayerReviewRecord(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['unverified_human_notes_only'] = 'unverified_human_notes_only'
    packet_sha256: str
    reviewer_claimed_label: str
    notes: list[ReviewerLayerNote]
    pending_layers: int = Field(ge=0)
    source_observation_modified: Literal[False] = False
    original_behavior_verified: Literal[False] = False
    interaction_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def build_level_packet(bundle: ObservationBundle, intake_dir: Path) -> ClaimLevelPacket:
    """Re-check *every* registered file before presenting any review candidate."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    verified_review = build_claim_review_packet(bundle, intake_dir)
    folder = _checked_folder(Path(intake_dir))
    path = folder / MANIFEST_NAME
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
        raise ValueError('missing or unsafe capture manifest')
    manifest = CaptureIntakeManifest.model_validate_json(path.read_text(encoding='utf-8'))
    if fingerprint(manifest) != verified_review.intake_manifest_sha256:
        raise ValueError('capture manifest changed since file verification')

    by_observation: dict[str, dict[EvidenceKind, list[str]]] = {
        x.id: {} for x in bundle.observations
    }
    for capture in manifest.entries:
        for observation_id in capture.proposal_observation_ids:
            by_observation[observation_id].setdefault(capture.evidence.kind, []).append(
                capture.evidence.id)

    items: list[LayerItem] = []
    for observation in sorted(bundle.observations, key=lambda x: x.id):
        evidence = by_observation[observation.id]
        visual = sorted(evidence.get(EvidenceKind.SCREENSHOT, []) +
                        evidence.get(EvidenceKind.DOM_TEXT, []))
        sequences = sorted(evidence.get(EvidenceKind.USER_DEMONSTRATION, []) +
                           evidence.get(EvidenceKind.MANUAL_TEST, []))
        before = observation.before
        after = observation.after
        changed = any(before.get(key) != after.get(key) for key in before.keys() & after.keys())
        has_reported_transition = bool(observation.action and before and after and changed)
        valid_sequence = bool(sequences and has_reported_transition and
                              observation.certainty is not Certainty.UNKNOWN)
        items.extend([
            LayerItem(
                observation_id=observation.id, layer=AssertionLayer.VISIBLE_STATE,
                evidence_ids=visual,
                status=(GateState.VISIBLE_REVIEW_CANDIDATE if visual else
                        GateState.MISSING_DIRECT_VISUAL_EVIDENCE),
                prerequisite_notes=(['A screenshot/DOM may illustrate only displayed values, not clicks or formulas.']
                                    if visual else ['Attach an authorized screenshot or sanitized DOM file.']),
                original_claim_certainty=observation.certainty),
            LayerItem(
                observation_id=observation.id, layer=AssertionLayer.INTERACTION_TRANSITION,
                evidence_ids=sequences if valid_sequence else [],
                status=(GateState.TRANSITION_REVIEW_CANDIDATE if valid_sequence else
                        GateState.MISSING_RECORDED_SEQUENCE),
                prerequisite_notes=([
                    'Reported action and a changed shared before/after field exist; human replay is still needed.'
                ] if valid_sequence else [
                    'Need an authorized demonstration/manual-test file, a declared action, changed before/after state, and a non-unknown source claim.'
                ]),
                original_claim_certainty=observation.certainty),
            LayerItem(
                observation_id=observation.id, layer=AssertionLayer.CALCULATION_FORMULA,
                evidence_ids=[], status=GateState.FORMULA_AUDIT_REQUIRED,
                prerequisite_notes=[
                    'Screenshots, displayed percentages and reported interaction do not prove a formula.',
                    'Independent calculation specification, inputs and expected outputs require separate audit.',
                ], original_claim_certainty=observation.certainty),
        ])
    return ClaimLevelPacket(
        source_observation_sha256=fingerprint(bundle),
        capture_manifest_sha256=fingerprint(manifest), items=items,
    )


def record_layer_notes(bundle: ObservationBundle, intake_dir: Path,
                       submission: LayerSubmission) -> LayerReviewRecord:
    """Always rebuild against the current files; cannot rely on a caller's packet."""
    current = build_level_packet(bundle, intake_dir)
    submission = LayerSubmission.model_validate(submission.model_dump(mode='json'))
    if submission.packet_sha256 != fingerprint(current):
        raise ValueError('stale or mismatched assertion-level review packet')
    available = {(x.observation_id, x.layer): x for x in current.items}
    for note in submission.notes:
        item = available.get((note.observation_id, note.layer))
        if item is None:
            raise ValueError('review note refers to nonexistent assertion layer')
        if set(note.evidence_ids_checked) - set(item.evidence_ids):
            raise ValueError('review note cites unlinked or ineligible evidence')
        if note.outcome == 'looks_consistent_but_not_verified':
            if not note.evidence_ids_checked:
                raise ValueError('appearance note requires a linked eligible capture')
            if item.status not in {
                GateState.VISIBLE_REVIEW_CANDIDATE,
                GateState.TRANSITION_REVIEW_CANDIDATE,
            }:
                raise ValueError('this assertion layer cannot be marked consistent')
            if item.original_claim_certainty is Certainty.UNKNOWN:
                raise ValueError('unknown claim cannot be marked consistent')
        if note.layer is AssertionLayer.CALCULATION_FORMULA and note.outcome != 'needs_more_evidence':
            raise ValueError('formula claims always require independent audit')
    return LayerReviewRecord(
        packet_sha256=fingerprint(current), reviewer_claimed_label=submission.reviewer_claimed_label,
        notes=sorted(submission.notes, key=lambda x: (x.observation_id, x.layer.value)),
        pending_layers=len(current.items) - len(submission.notes),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline layered claim notes: not verification or approval')
    parser.add_argument('command', choices=['packet', 'record'])
    parser.add_argument('observation', type=Path)
    parser.add_argument('capture_folder', type=Path)
    parser.add_argument('submission', nargs='?', type=Path)
    args = parser.parse_args(argv)
    if (args.command == 'record') != (args.submission is not None):
        parser.error('record requires submission; packet does not')
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        if args.command == 'record':
            note = LayerSubmission.model_validate_json(args.submission.read_text(encoding='utf-8'))
            result = record_layer_notes(bundle, args.capture_folder, note)
        else:
            result = build_level_packet(bundle, args.capture_folder)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
