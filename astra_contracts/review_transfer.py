"""Offline, read-only provenance checks for *unverified* review opinions.

Checks detect corruption and stale packets. SHA-256 is NOT a signature, nor
proof of identity, consent, ownership, approval, or original-site behavior.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from astra_contracts.generation_contract import fingerprint
from astra_contracts.reviewer_decisions import (
    RecordedItem, ReviewPacket, ReviewRecord, ReviewResponseItem,
    ReviewSubmission, record_opinions,
)

MAX_TRANSFER_BYTES = 65536


class ReviewTransferBundle(BaseModel):
    model_config = ConfigDict(extra='forbid')

    version: Literal['0.1'] = '0.1'
    purpose: Literal['unverified_opinion_transfer_only'] = 'unverified_opinion_transfer_only'
    source_packet_sha256: str
    record_sha256: str
    record: ReviewRecord
    identity_verified: Literal[False] = False
    approval_granted: Literal[False] = False
    db_access_authorized: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def validate_record(packet: ReviewPacket, record: ReviewRecord) -> ReviewRecord:
    """Reconstruct allowed opinions against the *current* packet, not just hashes.

    A caller can forge a hash: this detects internal inconsistencies, NOT
    maliciously recreated but structurally valid claimed opinions.
    """
    packet = ReviewPacket.model_validate(packet.model_dump(mode='json'))
    record = ReviewRecord.model_validate(record.model_dump(mode='json'))
    current_sha = fingerprint(packet)
    if record.packet_sha256 != current_sha:
        raise ValueError('stale review record: packet digest differs')
    if record.reviewer_claimed_label is None:
        raise ValueError('missing claimed reviewer label')
    submission = ReviewSubmission(
        version='0.1', packet_sha256=current_sha,
        reviewer_claimed_label=record.reviewer_claimed_label,
        responses=[ReviewResponseItem(
            item_id=x.item_id, decision=x.reviewer_opinion,
            rationale=x.rationale, evidence_refs_checked=x.evidence_refs_checked,
        ) for x in record.items if x.review_state == 'recorded_opinion'],
    )
    expected = record_opinions(packet, submission)
    if record.model_dump(mode='json') != expected.model_dump(mode='json'):
        raise ValueError('record contradicts current packet, status, counts or item order')
    return record


def export_bundle(packet: ReviewPacket, record: ReviewRecord) -> ReviewTransferBundle:
    record = validate_record(packet, record)
    bundle = ReviewTransferBundle(
        source_packet_sha256=fingerprint(packet), record_sha256=fingerprint(record), record=record,
    )
    if len(bundle.model_dump_json().encode('utf-8')) > MAX_TRANSFER_BYTES:
        raise ValueError('review export exceeds maximum size')
    return bundle


def import_bundle(packet: ReviewPacket, content: bytes) -> ReviewRecord:
    """Validate a byte-limited bundle from a non-authoritative local file."""
    if len(content) > MAX_TRANSFER_BYTES:
        raise ValueError('review transfer exceeds maximum size')
    bundle = ReviewTransferBundle.model_validate_json(content)
    if bundle.source_packet_sha256 != fingerprint(packet):
        raise ValueError('review transfer belongs to a different/stale packet')
    if bundle.record_sha256 != fingerprint(bundle.record):
        raise ValueError('review transfer record digest mismatch')
    return validate_record(packet, bundle.record)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Read-only opinion transfer integrity validator, no authorization')
    parser.add_argument('packet', type=Path, help='ReviewPacket JSON for current source')
    parser.add_argument('bundle', type=Path, help='ReviewTransferBundle JSON to verify')
    args = parser.parse_args(argv)
    try:
        packet = ReviewPacket.model_validate_json(args.packet.read_text(encoding='utf-8'))
        record = import_bundle(packet, args.bundle.read_bytes())
    except (OSError, ValueError, ValidationError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'valid_for_current_packet': True,
                      'authenticated': False, 'approved': False,
                      'recorded_opinions': record.recorded_opinion_count,
                      'packet_sha256': record.packet_sha256}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
