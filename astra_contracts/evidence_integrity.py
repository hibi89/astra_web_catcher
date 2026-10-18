"""Step 4-A continuation: offline observed-file inventory and integrity audit.

No fetching URLs, browser automation, interpretation of screenshots, proof of
capture ownership, change to underlying observation claims, or authorization.

    python -m astra_contracts.evidence_integrity snapshot OBSERVATION.json LOCAL_ROOT
    python -m astra_contracts.evidence_integrity verify OBSERVATION.json LOCAL_ROOT MANIFEST.json

Only stdout JSON is produced. `snapshot` is a self-declared *untrusted* baseline;
a matching file hash does not establish origin, truth, or user consent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Evidence, EvidenceKind, ObservationBundle

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PATH_LENGTH = 260
SAFE_PART = re.compile(r'^[\w .()\-]+$', re.UNICODE)
SENSITIVE_TEXT = re.compile(
    rb'(?i)(authorization\s*:\s*bearer|set-cookie\s*:|(?:access_token|refresh_token|api_key|client_secret|password)\s*[=:])'
)
ALLOWED_EXTENSIONS = {
    EvidenceKind.SCREENSHOT: {'.png', '.jpg', '.jpeg', '.webp'},
    EvidenceKind.DOM_TEXT: {'.txt', '.md'},
    EvidenceKind.USER_DEMONSTRATION: {'.txt', '.md', '.json'},
    EvidenceKind.SANITIZED_NETWORK: {'.json'},
    EvidenceKind.MANUAL_TEST: {'.txt', '.md', '.json'},
    EvidenceKind.ARCHIVED_REPORT: {'.md', '.txt'},
}
TEXT_EXTENSIONS = {'.txt', '.md', '.json'}


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class EvidenceFileEntry(ClosedModel):
    evidence_id: str
    source_ref: str
    kind: EvidenceKind
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    size_bytes: int = Field(ge=1, le=MAX_FILE_BYTES, strict=True)


class EvidenceFileManifest(ClosedModel):
    version: Literal['0.1'] = '0.1'
    source_kind: Literal['untrusted_local_snapshot'] = 'untrusted_local_snapshot'
    observation_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    capture_authenticity_verified: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    user_approval_granted: Literal[False] = False
    files: list[EvidenceFileEntry] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def no_duplicate_entries(self):
        ids = [f.evidence_id for f in self.files]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate evidence IDs in manifest')
        return self


class EvidenceFileFinding(ClosedModel):
    evidence_id: str
    kind: EvidenceKind
    status: Literal['bytes_match_untrusted', 'missing_file', 'hash_mismatch', 'size_mismatch', 'rejected_unsafe_file']
    detail: str


class EvidenceFileAudit(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['local_bytes_match_only', 'file_evidence_incomplete']
    observation_sha256: str
    manifest_sha256: str
    total_files: int
    bytes_matching: int
    archived_secondary_matching: int
    real_capture_verified: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    formula_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    approval_granted: Literal[False] = False
    findings: list[EvidenceFileFinding]


def _safe_parts(ref: str) -> tuple[str, ...]:
    if (not ref or len(ref) > MAX_PATH_LENGTH or '\\' in ref or ':' in ref
            or '?' in ref or '#' in ref or '%' in ref or ref.startswith(('/', '~'))):
        raise ValueError('unsafe evidence reference')
    parts = tuple(ref.split('/'))
    if (not parts or any(part in ('', '.', '..') or part.startswith('.') or
                         part.rstrip(' .') != part or not SAFE_PART.fullmatch(part)
                         for part in parts)):
        raise ValueError('unsafe evidence reference components')
    return parts


def _read_capture(root: Path, ev: Evidence) -> bytes:
    """Read strictly below root without following symlinks; never write or network fetch."""
    parts = _safe_parts(ev.source_ref)
    extension = Path(parts[-1]).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[ev.kind]:
        raise ValueError('evidence type/extension not accepted')
    if root.is_symlink() or not root.is_dir():
        raise ValueError('unsafe or absent evidence root')
    root_real = root.resolve(strict=True)
    cursor = root_real
    for part in parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('symbolic links in evidence path are forbidden')
    if not cursor.exists():
        raise FileNotFoundError('referenced local evidence file does not exist')
    if not cursor.is_file() or cursor.resolve(strict=True).is_relative_to(root_real) is False:
        raise ValueError('not a regular evidence file')
    if cursor.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('evidence file exceeds size cap')
    data = cursor.read_bytes()
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError('empty or oversized evidence file')
    if extension in TEXT_EXTENSIONS:
        data.decode('utf-8')
        if SENSITIVE_TEXT.search(data):
            raise ValueError('potential credentials in evidence text; sanitize before use')
        if extension == '.json':
            json.loads(data)
    elif extension == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('invalid PNG header')
    elif extension in {'.jpg', '.jpeg'} and not data.startswith(b'\xff\xd8\xff'):
        raise ValueError('invalid JPEG header')
    elif extension == '.webp' and not (data[:4] == b'RIFF' and data[8:12] == b'WEBP'):
        raise ValueError('invalid WEBP header')
    return data


def make_snapshot(bundle: ObservationBundle, root: Path) -> EvidenceFileManifest:
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    if not bundle.evidence:
        raise ValueError('cannot snapshot an observation with no evidence files')
    entries = []
    for ev in sorted(bundle.evidence, key=lambda e: e.id):
        data = _read_capture(Path(root), ev)
        entries.append(EvidenceFileEntry(evidence_id=ev.id, source_ref=ev.source_ref,
            kind=ev.kind, sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data)))
    return EvidenceFileManifest(observation_sha256=fingerprint(bundle), files=entries)


def audit_files(bundle: ObservationBundle, root: Path,
                manifest: EvidenceFileManifest) -> EvidenceFileAudit:
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    manifest = EvidenceFileManifest.model_validate(manifest.model_dump(mode='json'))
    if fingerprint(bundle) != manifest.observation_sha256:
        raise ValueError('manifest for different observation bundle')
    references = {e.id: e for e in bundle.evidence}
    if set(references) != {entry.evidence_id for entry in manifest.files}:
        raise ValueError('manifest evidence IDs differ from observation bundle')
    findings = []
    for entry in sorted(manifest.files, key=lambda f: f.evidence_id):
        evidence = references[entry.evidence_id]
        if entry.kind != evidence.kind or entry.source_ref != evidence.source_ref:
            raise ValueError('manifest metadata differs from observation bundle')
        try:
            data = _read_capture(Path(root), evidence)
        except FileNotFoundError:
            status, detail = 'missing_file', 'Referenced local evidence file is absent.'
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            status, detail = 'rejected_unsafe_file', 'Evidence file failed path, content or safety checks.'
        else:
            if len(data) != entry.size_bytes:
                status, detail = 'size_mismatch', 'Evidence file length differs from declared snapshot.'
            elif hashlib.sha256(data).hexdigest() != entry.sha256:
                status, detail = 'hash_mismatch', 'Evidence file bytes differ from declared snapshot.'
            else:
                status, detail = 'bytes_match_untrusted', 'Local bytes match a self-declared baseline; origin and claims unverified.'
        findings.append(EvidenceFileFinding(evidence_id=evidence.id, kind=evidence.kind,
                                             status=status, detail=detail))
    count = sum(x.status == 'bytes_match_untrusted' for x in findings)
    return EvidenceFileAudit(status='local_bytes_match_only' if count == len(findings)
                             else 'file_evidence_incomplete',
                             observation_sha256=manifest.observation_sha256,
                             manifest_sha256=fingerprint(manifest), total_files=len(findings),
                             bytes_matching=count,
                             archived_secondary_matching=sum(x.kind is EvidenceKind.ARCHIVED_REPORT
                             and x.status == 'bytes_match_untrusted' for x in findings),
                             findings=findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline source-evidence file audit (not origin verification)')
    parser.add_argument('action', choices=['snapshot', 'verify'])
    parser.add_argument('observation', type=Path)
    parser.add_argument('local_root', type=Path)
    parser.add_argument('manifest', type=Path, nargs='?')
    args = parser.parse_args(argv)
    if (args.action == 'verify') != (args.manifest is not None):
        parser.error('verify needs manifest; snapshot accepts no manifest')
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        if args.action == 'snapshot':
            result = make_snapshot(bundle, args.local_root)
        else:
            declared = EvidenceFileManifest.model_validate_json(args.manifest.read_text(encoding='utf-8'))
            result = audit_files(bundle, args.local_root, declared)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
