"""Offline, untrusted capture-to-observation human triage (NOT approval).

Runs on previously registered local captures only. It NEVER upgrades source
ObservationBundle certainty or verifies provenance, formulas, ownership or site
behavior. No live browser, customer DB, network, source writes or deployment.

Usage:
  python -m astra_contracts.capture_claim_review packet OBSERVATION.json INTAKE_DIR
  python -m astra_contracts.capture_claim_review record OBSERVATION.json INTAKE_DIR RESPONSE.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.capture_intake import (
    MANIFEST_NAME, CaptureIntakeManifest, _checked_folder, verify_captures,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Certainty, EvidenceKind, Feature, ObservationBundle


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ClaimReviewItem(ClosedModel):
    observation_id: str
    feature: Feature
    certainty_at_source: Certainty
    title: str
    claim: str
    capture_ids: list[str]
    visible_capture_ids: list[str]
    linked_evidence_is_unverified: Literal[True] = True


class ClaimReviewPacket(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['manual_capture_claim_review_pending'] = 'manual_capture_claim_review_pending'
    original_bundle_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    intake_manifest_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_evidence_count: int = Field(ge=1)
    byte_integrity_passed: Literal[True] = True
    capture_authenticity_verified: Literal[False] = False
    original_behavior_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    authorization_granted: Literal[False] = False
    items: list[ClaimReviewItem] = Field(min_length=1, max_length=500)


class ClaimReviewOpinion(ClosedModel):
    observation_id: str
    decision: Literal['more_evidence_needed', 'appears_consistent_with_visible_capture',
                      'appears_inconsistent_with_visible_capture']
    capture_ids_checked: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(min_length=8, max_length=1200)

    @model_validator(mode='after')
    def no_duplicate_capture_ids(self):
        if len(set(self.capture_ids_checked)) != len(self.capture_ids_checked):
            raise ValueError('duplicate checked capture IDs')
        return self


class ClaimReviewSubmission(ClosedModel):
    version: Literal['0.1']
    packet_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer_claimed_label: str = Field(min_length=2, max_length=100)
    opinions: list[ClaimReviewOpinion] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique_observation_ids(self):
        keys = [x.observation_id for x in self.opinions]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate observation opinion')
        return self


class ClaimReviewRecord(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['unverified_opinion_record_only'] = 'unverified_opinion_record_only'
    packet_sha256: str
    reviewer_claimed_label: str
    opinions: list[ClaimReviewOpinion]
    review_item_count: int = Field(ge=1)
    recorded_opinion_count: int = Field(ge=1)
    pending_review_count: int = Field(ge=0)
    original_bundle_modified: Literal[False] = False
    original_behavior_verified: Literal[False] = False
    capture_authenticity_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    mapping_approved: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def build_claim_review_packet(bundle: ObservationBundle, intake_dir: Path) -> ClaimReviewPacket:
    """Reject any stale/modified/missing capture rather than proposing conclusions."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    folder = _checked_folder(Path(intake_dir))
    audit = verify_captures(bundle, folder)
    if (audit.result != 'bytes_match_untrusted'
            or audit.bytes_matching != audit.captured_file_count):
        raise ValueError('all registered capture files must pass the byte-integrity check')
    manifest_path = folder / MANIFEST_NAME
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or manifest_path.stat().st_size > 256 * 1024):
        raise ValueError('unsafe or missing capture manifest')
    manifest = CaptureIntakeManifest.model_validate_json(manifest_path.read_text(encoding='utf-8'))
    if fingerprint(manifest) != audit.manifest_sha256:
        raise ValueError('capture audit/manifest mismatch')
    linked: dict[str, list[str]] = {x.id: [] for x in bundle.observations}
    visible: dict[str, list[str]] = {x.id: [] for x in bundle.observations}
    for entry in manifest.entries:
        for id_ in entry.proposal_observation_ids:
            linked[id_].append(entry.evidence.id)
            if entry.evidence.kind in {EvidenceKind.SCREENSHOT, EvidenceKind.DOM_TEXT}:
                visible[id_].append(entry.evidence.id)
    return ClaimReviewPacket(
        original_bundle_sha256=fingerprint(bundle),
        intake_manifest_sha256=fingerprint(manifest),
        source_evidence_count=len(manifest.entries),
        items=[ClaimReviewItem(
            observation_id=o.id, feature=o.feature, certainty_at_source=o.certainty,
            title=o.title, claim=o.claim, capture_ids=sorted(linked[o.id]),
            visible_capture_ids=sorted(visible[o.id]))
            for o in sorted(bundle.observations, key=lambda item: item.id)],
    )


def record_claim_opinions(packet: ClaimReviewPacket,
                          submission: ClaimReviewSubmission) -> ClaimReviewRecord:
    """Opinions are attributable only to an unverified *claimed* label."""
    packet = ClaimReviewPacket.model_validate(packet.model_dump(mode='json'))
    submission = ClaimReviewSubmission.model_validate(submission.model_dump(mode='json'))
    if submission.packet_sha256 != fingerprint(packet):
        raise ValueError('stale or mismatched claim review packet')
    indexed = {item.observation_id: item for item in packet.items}
    accepted: list[ClaimReviewOpinion] = []
    for opinion in submission.opinions:
        candidate = indexed.get(opinion.observation_id)
        if candidate is None:
            raise ValueError('claim opinion points to unknown observation')
        if set(opinion.capture_ids_checked) - set(candidate.capture_ids):
            raise ValueError('claim opinion cites an unlinked capture')
        if opinion.decision != 'more_evidence_needed':
            if not opinion.capture_ids_checked:
                raise ValueError('an appearance comparison needs checked capture IDs')
            if set(opinion.capture_ids_checked) - set(candidate.visible_capture_ids):
                raise ValueError('appearance opinion needs screenshot or DOM evidence')
            if (candidate.certainty_at_source is Certainty.UNKNOWN
                    and opinion.decision == 'appears_consistent_with_visible_capture'):
                raise ValueError('unknown behavior cannot be marked visually consistent')
        accepted.append(opinion)
    return ClaimReviewRecord(
        packet_sha256=fingerprint(packet), reviewer_claimed_label=submission.reviewer_claimed_label,
        opinions=sorted(accepted, key=lambda x: x.observation_id),
        review_item_count=len(packet.items), recorded_opinion_count=len(accepted),
        pending_review_count=len(packet.items)-len(accepted),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline capture-linked review, not proof or approval')
    parser.add_argument('action', choices=['packet', 'record'])
    parser.add_argument('observation', type=Path)
    parser.add_argument('intake_directory', type=Path)
    parser.add_argument('submission', nargs='?', type=Path)
    args = parser.parse_args(argv)
    if (args.action == 'record') != (args.submission is not None):
        parser.error('record needs a submission; packet needs none')
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        packet = build_claim_review_packet(bundle, args.intake_directory)
        if args.action == 'record':
            submitted = ClaimReviewSubmission.model_validate_json(args.submission.read_text(encoding='utf-8'))
            output = record_claim_opinions(packet, submitted)
        else:
            output = packet
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(output.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
