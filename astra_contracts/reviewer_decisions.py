"""Step 4-C: offline reviewer decision records for source evidence and field meaning.

No connection to any service, authentication, change to a database, or grant of
permissions. Review labels represent an *unverified human claim*, not consent.

CLI:
  python -m astra_contracts.reviewer_decisions packet SPEC SCHEMA REPORT
  python -m astra_contracts.reviewer_decisions record SPEC SCHEMA REPORT SUBMISSION
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import fingerprint


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ItemKind(str, Enum):
    OBSERVED_BEHAVIOR = 'observed_behavior'
    UNRESOLVED_BEHAVIOR = 'unresolved_behavior'
    FIELD_SEMANTICS = 'field_semantics'


class ReviewItem(ClosedModel):
    item_id: str = Field(min_length=1, max_length=180)
    kind: ItemKind
    observation_id: str
    field_name: str | None = None
    description: str = Field(min_length=1, max_length=1000)
    archived_evidence_only: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    mapping_status: str | None = None


class ReviewPacket(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['pending_human_review'] = 'pending_human_review'
    spec_sha256: str
    schema_sha256: str
    mapping_report_sha256: str
    source_schema_verified_live: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    approval_verified: Literal[False] = False
    implementation_ready: Literal[False] = False
    items: list[ReviewItem] = Field(min_length=1)


class HumanDecision(str, Enum):
    SUPPORTED_AS_PROPOSAL = 'supported_as_proposal'
    NEEDS_MORE_EVIDENCE = 'needs_more_evidence'
    REJECTED_FOR_TARGET = 'rejected_for_target'


class ReviewResponseItem(ClosedModel):
    item_id: str
    decision: HumanDecision
    rationale: str = Field(min_length=8, max_length=1200)
    evidence_refs_checked: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def unique_references(self):
        if len(self.evidence_refs_checked) != len(set(self.evidence_refs_checked)):
            raise ValueError('duplicate references checked')
        return self


class ReviewSubmission(ClosedModel):
    version: Literal['0.1']
    packet_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer_claimed_label: str = Field(min_length=2, max_length=100)
    responses: list[ReviewResponseItem] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [r.item_id for r in self.responses]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate review response IDs')
        return self


class RecordedItem(ClosedModel):
    item_id: str
    review_state: Literal['pending', 'recorded_opinion']
    reviewer_opinion: HumanDecision | None = None
    rationale: str | None = None
    evidence_refs_checked: list[str] = Field(default_factory=list)


class ReviewRecord(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['opinion_record_only_not_authorization'] = 'opinion_record_only_not_authorization'
    packet_sha256: str
    reviewer_claimed_label: str | None
    reviewer_identity_verified: Literal[False] = False
    reference_behavior_verified: Literal[False] = False
    field_meanings_verified: Literal[False] = False
    schema_verified_live: Literal[False] = False
    user_approval_verified: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    database_access_authorized: Literal[False] = False
    source_changes_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    pending_count: int = Field(ge=0)
    recorded_opinion_count: int = Field(ge=0)
    items: list[RecordedItem]


def _key(kind: str, observation_id: str, field: str = '') -> str:
    # Full SHA-256 of potentially arbitrary state key avoids unsafe identifiers.
    return f'{kind}:{observation_id}' + (':' + hashlib.sha256(field.encode('utf-8')).hexdigest() if field else '')


def build_packet(spec: FunctionalSpecDraft, schema: OwnedSchemaDeclaration,
                 report: MappingReport) -> ReviewPacket:
    """Regenerate the mapping report rather than trusting caller-supplied counts."""
    spec = FunctionalSpecDraft.model_validate(spec.model_dump(mode='json'))
    schema = OwnedSchemaDeclaration.model_validate(schema.model_dump(mode='json'))
    report = MappingReport.model_validate(report.model_dump(mode='json'))
    expected = compare_mappings(spec, schema)
    if report.model_dump(mode='json') != expected.model_dump(mode='json'):
        raise ValueError('mapping report differs from recalculated spec/schema declaration')
    items: list[ReviewItem] = []
    for candidate in sorted(spec.candidate_features, key=lambda x: x.observation_id):
        items.append(ReviewItem(
            item_id=_key('behavior', candidate.observation_id),
            kind=ItemKind.OBSERVED_BEHAVIOR,
            observation_id=candidate.observation_id,
            description=candidate.claim,
            archived_evidence_only=candidate.evidence_quality.value == 'archived_secondary',
            evidence_refs=[e.source_ref for e in candidate.evidence],
        ))
    for unresolved in sorted(spec.unresolved, key=lambda x: x.observation_id):
        items.append(ReviewItem(
            item_id=_key('unresolved', unresolved.observation_id),
            kind=ItemKind.UNRESOLVED_BEHAVIOR,
            observation_id=unresolved.observation_id,
            description=unresolved.claim,
        ))
    for finding in sorted(report.findings, key=lambda x: (x.observation_id, x.ui_field)):
        target = (f'{finding.resource_id}.{finding.resource_field}' if
                  finding.resource_id and finding.resource_field else 'NOT MAPPED')
        items.append(ReviewItem(
            item_id=_key('field', finding.observation_id, finding.ui_field),
            kind=ItemKind.FIELD_SEMANTICS,
            observation_id=finding.observation_id,
            field_name=finding.ui_field,
            description=f'Declared mapping {finding.ui_field} -> {target}: {finding.detail}',
            mapping_status=finding.status,
        ))
    ids = [i.item_id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate review item identities')
    if not items:
        raise ValueError('no review items to record')
    return ReviewPacket(spec_sha256=fingerprint(spec), schema_sha256=fingerprint(schema),
                        mapping_report_sha256=fingerprint(report), items=items)


def record_opinions(packet: ReviewPacket, submission: ReviewSubmission) -> ReviewRecord:
    """Record a claimed reviewer's opinions, **never** verify their identity/approval."""
    packet = ReviewPacket.model_validate(packet.model_dump(mode='json'))
    submission = ReviewSubmission.model_validate(submission.model_dump(mode='json'))
    if submission.packet_sha256 != fingerprint(packet):
        raise ValueError('stale or mismatched review packet fingerprint')
    known = {item.item_id: item for item in packet.items}
    responses = {item.item_id: item for item in submission.responses}
    if set(responses) - set(known):
        raise ValueError('review response references a nonexistent item')
    for item_id, response in responses.items():
        known_evidence = set(known[item_id].evidence_refs)
        if set(response.evidence_refs_checked) - known_evidence:
            raise ValueError('review response cites evidence not attached to that item')
        if (response.decision == HumanDecision.SUPPORTED_AS_PROPOSAL
                and known[item_id].kind == ItemKind.UNRESOLVED_BEHAVIOR):
            raise ValueError('unknown behavior cannot be declared supported as a proposal')
        if (response.decision == HumanDecision.SUPPORTED_AS_PROPOSAL
                and known[item_id].kind == ItemKind.FIELD_SEMANTICS
                and known[item_id].mapping_status != 'structurally_compatible_unapproved'):
            raise ValueError('unresolved or incompatible mapping cannot be marked supported')
        if (response.decision == HumanDecision.SUPPORTED_AS_PROPOSAL
                and known[item_id].kind == ItemKind.OBSERVED_BEHAVIOR
                and known[item_id].archived_evidence_only):
            raise ValueError('archived report alone is not firsthand verification')
    recorded = [RecordedItem(item_id=item.item_id,
                 review_state='recorded_opinion' if item.item_id in responses else 'pending',
                 reviewer_opinion=responses[item.item_id].decision if item.item_id in responses else None,
                 rationale=responses[item.item_id].rationale if item.item_id in responses else None,
                 evidence_refs_checked=responses[item.item_id].evidence_refs_checked if item.item_id in responses else [])
                for item in packet.items]
    return ReviewRecord(packet_sha256=fingerprint(packet),
                        reviewer_claimed_label=submission.reviewer_claimed_label,
                        pending_count=sum(x.review_state == 'pending' for x in recorded),
                        recorded_opinion_count=len(responses), items=recorded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline review packet and opinion record (not authorization)')
    parser.add_argument('command', choices=['packet', 'record'])
    parser.add_argument('spec', type=Path)
    parser.add_argument('schema', type=Path)
    parser.add_argument('mapping_report', type=Path)
    parser.add_argument('submission', nargs='?', type=Path)
    args = parser.parse_args(argv)
    if (args.command == 'record') != (args.submission is not None):
        parser.error('record requires a submission; packet does not accept one')
    try:
        spec = FunctionalSpecDraft.model_validate_json(args.spec.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.schema.read_text(encoding='utf-8'))
        report = MappingReport.model_validate_json(args.mapping_report.read_text(encoding='utf-8'))
        packet = build_packet(spec, schema, report)
        if args.command == 'record':
            submission = ReviewSubmission.model_validate_json(args.submission.read_text(encoding='utf-8'))
            print(record_opinions(packet, submission).model_dump_json(indent=2))
        else:
            print(packet.model_dump_json(indent=2))
        return 0
    except (ValueError, ValidationError, OSError, UnicodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
