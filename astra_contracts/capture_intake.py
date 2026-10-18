"""Register locally supplied UI evidence bytes into an isolated, unapproved intake.

No browser, network or DB access; this does not change observation claims, assert
capture authenticity, or authorize implementation. Output is under an empty
astra-capture-* folder directly below the system temporary directory.

CLI: python -m astra_contracts.capture_intake register BUNDLE SOURCE_ROOT REQUEST EMPTY_TEMP_DIR
     python -m astra_contracts.capture_intake verify BUNDLE INTAKE_DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.evidence_integrity import _read_capture, _safe_parts, ALLOWED_EXTENSIONS, MAX_FILE_BYTES
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Evidence, EvidenceKind, ObservationBundle, ID_PATTERN

ELIGIBLE_KINDS = {EvidenceKind.SCREENSHOT, EvidenceKind.DOM_TEXT,
                  EvidenceKind.USER_DEMONSTRATION, EvidenceKind.SANITIZED_NETWORK,
                  EvidenceKind.MANUAL_TEST}
MANIFEST_NAME = 'capture_intake.json'


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ProposedCapture(ClosedModel):
    evidence: Evidence
    observation_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def no_claim_upgrade(self):
        if self.evidence.kind not in ELIGIBLE_KINDS:
            raise ValueError('archived reports are not new direct capture evidence')
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError('duplicate referenced observations')
        return self


class CaptureIntakeRequest(ClosedModel):
    version: Literal['0.1']
    source_kind: Literal['manually_supplied_local_files']
    observation_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    captures: list[ProposedCapture] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique_input(self):
        ids = [x.evidence.id for x in self.captures]
        refs = [x.evidence.source_ref.casefold() for x in self.captures]
        if len(ids) != len(set(ids)) or len(refs) != len(set(refs)):
            raise ValueError('duplicate capture ID or source reference')
        return self


class IntakeEntry(ClosedModel):
    evidence: Evidence
    proposal_observation_ids: list[str] = Field(min_length=1)
    stored_ref: str = Field(pattern=r'^captures/[a-z][a-z0-9_-]{1,63}\.(png|jpe?g|webp|txt|md|json)$')
    size_bytes: int = Field(ge=1, le=MAX_FILE_BYTES, strict=True)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_claim: Literal['unverified_operator_supplied'] = 'unverified_operator_supplied'
    behavior_claim_upgraded: Literal[False] = False


class CaptureIntakeManifest(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['pending_manual_evidence_review'] = 'pending_manual_evidence_review'
    original_bundle_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    request_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_bundle_unchanged: Literal[True] = True
    original_site_behavior_verified: Literal[False] = False
    screenshot_authenticity_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    user_approval_verified: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    entries: list[IntakeEntry] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique_entries(self):
        ids = [x.evidence.id for x in self.entries]
        refs = [x.stored_ref.casefold() for x in self.entries]
        if len(ids) != len(set(ids)) or len(refs) != len(set(refs)):
            raise ValueError('duplicate registered capture')
        return self


class IntakeVerification(ClosedModel):
    version: Literal['0.1'] = '0.1'
    result: Literal['bytes_match_untrusted', 'evidence_incomplete']
    original_bundle_sha256: str
    manifest_sha256: str
    captured_file_count: int
    bytes_matching: int
    findings: list[dict[str, str]]
    capture_authenticity_verified: Literal[False] = False
    original_behavior_verified: Literal[False] = False
    approval_verified: Literal[False] = False


def _empty_destination(folder: Path) -> Path:
    temp_parent = Path(tempfile.gettempdir()).resolve()
    if (folder.is_symlink() or not folder.is_dir()
            or folder.parent.resolve() != temp_parent or folder.resolve().parent != temp_parent
            or not folder.name.startswith('astra-capture-') or any(folder.iterdir())):
        raise ValueError('destination must be a new empty astra-capture-* folder under system temp')
    return folder


def _checked_folder(folder: Path) -> Path:
    temp_parent = Path(tempfile.gettempdir()).resolve()
    if (folder.is_symlink() or not folder.is_dir()
            or folder.parent.resolve() != temp_parent or folder.resolve().parent != temp_parent
            or not folder.name.startswith('astra-capture-')):
        raise ValueError('intake directory must remain inside the system temporary directory')
    return folder


def _check_request(bundle: ObservationBundle, request: CaptureIntakeRequest) -> None:
    if request.observation_sha256 != fingerprint(bundle):
        raise ValueError('stale observation bundle hash')
    observation_ids = {ob.id for ob in bundle.observations}
    evidence_ids = {ev.id for ev in bundle.evidence}
    for proposed in request.captures:
        if proposed.evidence.id in evidence_ids:
            raise ValueError('incoming evidence ID collides with existing source evidence')
        if set(proposed.observation_ids) - observation_ids:
            raise ValueError('incoming evidence references an unknown observation')
        _safe_parts(proposed.evidence.source_ref)


def register_captures(bundle: ObservationBundle, source_root: Path,
                      request: CaptureIntakeRequest, output_root: Path) -> CaptureIntakeManifest:
    """Copy only checked local files; never edit original bundle, DB or inputs."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    request = CaptureIntakeRequest.model_validate(request.model_dump(mode='json'))
    _check_request(bundle, request)
    root = _empty_destination(Path(output_root))
    # Prevalidate the *entire* batch before writing any file.
    prepared: list[tuple[ProposedCapture, bytes, str]] = []
    total = 0
    for proposed in request.captures:
        data = _read_capture(Path(source_root), proposed.evidence)
        total += len(data)
        if total > 20 * MAX_FILE_BYTES:
            raise ValueError('capture batch too large')
        ext = Path(proposed.evidence.source_ref).suffix.lower()
        stored = f'captures/{proposed.evidence.id}{ext}'
        prepared.append((proposed, data, stored))
    if len({x[2].casefold() for x in prepared}) != len(prepared):
        raise ValueError('stored file collision')
    entries = [IntakeEntry(evidence=x.evidence, proposal_observation_ids=sorted(x.observation_ids),
              stored_ref=stored, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
              for x, data, stored in prepared]
    manifest = CaptureIntakeManifest(original_bundle_sha256=fingerprint(bundle),
                request_sha256=fingerprint(request), entries=entries)
    _empty_destination(root)  # check again before first write
    (root / 'captures').mkdir(mode=0o700)
    for _, data, stored in prepared:
        with (root / stored).open('xb') as out:
            out.write(data)
    with (root / MANIFEST_NAME).open('x', encoding='utf-8') as out:
        out.write(manifest.model_dump_json(indent=2) + '\n')
    return manifest


def verify_captures(bundle: ObservationBundle, root: Path) -> IntakeVerification:
    """Recheck registered byte integrity only; not a proof of original capture."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    folder = _checked_folder(Path(root))
    manifest_file = folder / MANIFEST_NAME
    if manifest_file.is_symlink() or not manifest_file.is_file() or manifest_file.stat().st_size > 256 * 1024:
        raise ValueError('missing, symlinked or oversized manifest')
    manifest = CaptureIntakeManifest.model_validate_json(manifest_file.read_text(encoding='utf-8'))
    if fingerprint(bundle) != manifest.original_bundle_sha256:
        raise ValueError('intake manifest for a different observation bundle')
    known_ids = {ob.id for ob in bundle.observations}
    source_evidence = {x.id for x in bundle.evidence}
    findings: list[dict[str, str]] = []
    for item in manifest.entries:
        if item.evidence.id in source_evidence or set(item.proposal_observation_ids) - known_ids:
            raise ValueError('intake manifest references an invalid observation or evidence ID')
        expected_ref = f'captures/{item.evidence.id}{Path(item.evidence.source_ref).suffix.lower()}'
        if item.stored_ref != expected_ref:
            raise ValueError('intake stored path does not match capture metadata')
        synthetic_ev = item.evidence.model_copy(update={'source_ref': expected_ref})
        try:
            data = _read_capture(folder, synthetic_ev)
        except FileNotFoundError:
            result = 'missing_file'
        except (OSError, UnicodeError, ValueError):
            result = 'rejected_unsafe_file'
        else:
            if len(data) != item.size_bytes:
                result = 'size_mismatch'
            elif hashlib.sha256(data).hexdigest() != item.sha256:
                result = 'hash_mismatch'
            else:
                result = 'bytes_match_untrusted'
        findings.append({'evidence_id': item.evidence.id, 'result': result})
    matched = sum(x['result'] == 'bytes_match_untrusted' for x in findings)
    return IntakeVerification(result='bytes_match_untrusted' if matched == len(findings)
                     else 'evidence_incomplete', original_bundle_sha256=fingerprint(bundle),
                     manifest_sha256=fingerprint(manifest), captured_file_count=len(findings),
                     bytes_matching=matched, findings=findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline unapproved local capture intake')
    sub = parser.add_subparsers(dest='action', required=True)
    reg = sub.add_parser('register')
    for name in ('bundle', 'source_root', 'request', 'empty_destination'):
        reg.add_argument(name, type=Path)
    ver = sub.add_parser('verify')
    ver.add_argument('bundle', type=Path)
    ver.add_argument('intake_folder', type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.bundle.read_text(encoding='utf-8'))
        if args.action == 'register':
            request = CaptureIntakeRequest.model_validate_json(args.request.read_text(encoding='utf-8'))
            result = register_captures(bundle, args.source_root, request, args.empty_destination)
        else:
            result = verify_captures(bundle, args.intake_folder)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
