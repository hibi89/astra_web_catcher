"""Offline file-byte integrity checks never verify a site's original behavior."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.evidence_integrity import (
    EvidenceFileManifest, EvidenceFileAudit, audit_files, make_snapshot, main,
)
from astra_contracts.observation import ObservationBundle

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/jp_nail_brand_filter_observation_20261018.json'
GOLDEN = ROOT / 'fixtures/jp_nail_evidence_file_snapshot_20261018.json'


def original():
    return ObservationBundle.model_validate_json(FIXTURE.read_text(encoding='utf-8'))


def fixture_for(tmp_path: Path, *, kind='archived_report', name='evidence/example.md', data=b'example report'):
    obj = original().model_dump(mode='json')
    obj['evidence'][0]['kind'] = kind
    obj['evidence'][0]['source_ref'] = name
    obj['observations'][0]['evidence_ids'] = [obj['evidence'][0]['id']]
    root = tmp_path / 'local'
    (root / 'evidence').mkdir(parents=True)
    destination = root / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return ObservationBundle.model_validate(obj), root, destination


def test_archived_source_exists_and_snapshot_is_deterministic():
    model = make_snapshot(original(), ROOT)
    assert model.model_dump(mode='json') == json.loads(GOLDEN.read_text(encoding='utf-8'))
    assert model.source_kind == 'untrusted_local_snapshot'
    assert not model.original_site_behavior_verified


def test_historical_archive_is_only_secondary_integrity():
    report = audit_files(original(), ROOT, EvidenceFileManifest.model_validate_json(GOLDEN.read_text()))
    assert report.status == 'local_bytes_match_only'
    assert report.bytes_matching == 1
    assert report.archived_secondary_matching == 1
    assert report.findings[0].status == 'bytes_match_untrusted'
    assert report.real_capture_verified is False
    assert report.original_site_behavior_verified is False
    assert report.approval_granted is False


def test_hash_change_same_size_is_detected(tmp_path):
    bundle, root, path = fixture_for(tmp_path, data=b'123456')
    snap = make_snapshot(bundle, root)
    path.write_bytes(b'654321')
    report = audit_files(bundle, root, snap)
    assert report.findings[0].status == 'hash_mismatch'
    assert report.bytes_matching == 0


def test_size_change_is_detected(tmp_path):
    bundle, root, path = fixture_for(tmp_path)
    snap = make_snapshot(bundle, root)
    path.write_bytes(b'longer file than original')
    assert audit_files(bundle, root, snap).findings[0].status == 'size_mismatch'


def test_missing_file_is_recorded_not_silently_ignored(tmp_path):
    bundle, root, path = fixture_for(tmp_path)
    snap = make_snapshot(bundle, root)
    path.unlink()
    report = audit_files(bundle, root, snap)
    assert report.findings[0].status == 'missing_file'
    assert report.status == 'file_evidence_incomplete'


def test_second_manifest_version_or_approval_forgery_is_rejected():
    snap = json.loads(GOLDEN.read_text())
    for field, value in [('user_approval_granted', True), ('original_site_behavior_verified', True),
                         ('source_kind', 'verified_source'), ('version', '9.9')]:
        change = {**snap, field: value}
        with pytest.raises(ValidationError):
            EvidenceFileManifest.model_validate(change)


def test_report_cannot_claim_source_proof():
    report = audit_files(original(), ROOT, EvidenceFileManifest.model_validate_json(GOLDEN.read_text()))
    wrong = report.model_dump(mode='json')
    for field in ('real_capture_verified','original_site_behavior_verified','formula_verified',
                  'reviewer_identity_verified','approval_granted'):
        wrong_field = {**wrong, field: True}
        with pytest.raises(ValidationError):
            EvidenceFileAudit.model_validate(wrong_field)


def test_stale_bundle_fingerprint_rejected():
    data = original().model_dump(mode='json')
    data['scope'] += ' amended'
    snap = EvidenceFileManifest.model_validate_json(GOLDEN.read_text())
    with pytest.raises(ValueError, match='different observation bundle'):
        audit_files(ObservationBundle.model_validate(data), ROOT, snap)


def test_swapped_evidence_refs_rejected():
    snap = json.loads(GOLDEN.read_text())
    snap['files'][0]['source_ref'] = 'evidence/other.md'
    with pytest.raises(ValueError, match='metadata differs'):
        audit_files(original(), ROOT, EvidenceFileManifest.model_validate(snap))


def test_unknown_or_duplicate_evidence_id_rejected():
    snap = json.loads(GOLDEN.read_text())
    extra = copy.deepcopy(snap)
    extra['files'][0]['evidence_id'] = 'different_id'
    with pytest.raises(ValueError, match='evidence IDs differ'):
        audit_files(original(), ROOT, EvidenceFileManifest.model_validate(extra))
    snap['files'].append(snap['files'][0])
    with pytest.raises(ValidationError, match='duplicate evidence IDs'):
        EvidenceFileManifest.model_validate(snap)


@pytest.mark.parametrize('ref', [
    '../outside.md', 'evidence/../outside.md', '/tmp/archive.md',
    'evidence\\capture.md', 'evidence/.private.md',
    'evidence/x%2e%2e.md', 'evidence//x.md', 'evidence/x.md?token=x',
    'http://example.com/x.md', 'evidence/X:source.md',
    'evidence/name.md ',
])
def test_traversal_and_unsafe_paths_refused(tmp_path, ref):
    b, root, _ = fixture_for(tmp_path)
    raw = b.model_dump(mode='json')
    raw['evidence'][0]['source_ref'] = ref
    try:
        b = ObservationBundle.model_validate(raw)
    except ValidationError:
        return  # lower-level contract already blocks it
    with pytest.raises(ValueError, match='unsafe'):
        make_snapshot(b, root)


def test_symlinked_evidence_file_refused(tmp_path):
    b, root, file = fixture_for(tmp_path)
    file.unlink()
    external = tmp_path / 'secret.md'
    external.write_text('private', encoding='utf-8')
    file.symlink_to(external)
    with pytest.raises(ValueError, match='symbolic'):
        make_snapshot(b, root)


def test_symlinked_intermediate_folder_refused(tmp_path):
    b, root, file = fixture_for(tmp_path)
    file.unlink()
    (root/'evidence').rmdir()
    elsewhere = tmp_path/'elsewhere'
    elsewhere.mkdir()
    (elsewhere/'example.md').write_text('some evidence', encoding='utf-8')
    (root/'evidence').symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match='symbolic'):
        make_snapshot(b, root)


def test_wrong_extension_to_kind_rejected(tmp_path):
    b, root, _ = fixture_for(tmp_path, kind='screenshot')
    with pytest.raises(ValueError, match='extension'):
        make_snapshot(b, root)


def test_fake_png_rejected(tmp_path):
    b, root, _ = fixture_for(tmp_path, kind='screenshot', name='evidence/fake.png', data=b'fake png')
    with pytest.raises(ValueError, match='PNG header'):
        make_snapshot(b, root)


def test_png_header_present_is_only_bytes_not_truth(tmp_path):
    b, root, _ = fixture_for(tmp_path, kind='screenshot', name='evidence/mock.png',
                            data=b'\x89PNG\r\n\x1a\nminimal-fake-content')
    manifest = make_snapshot(b, root)
    report = audit_files(b, root, manifest)
    assert report.archived_secondary_matching == 0
    assert report.real_capture_verified is False  # magic bytes do not prove source


def test_text_secret_pattern_blocks_snapshot(tmp_path):
    b, root, file = fixture_for(tmp_path, data=b'Authorization: Bearer sample-value')
    with pytest.raises(ValueError, match='credentials'):
        make_snapshot(b, root)


def test_invalid_utf8_and_json_rejected(tmp_path):
    b, root, file = fixture_for(tmp_path, data=b'\xff\x00')
    with pytest.raises(UnicodeError):
        make_snapshot(b, root)
    b2, root2, _ = fixture_for(tmp_path/'second', kind='sanitized_network',
                              name='evidence/net.json', data=b'{invalid')
    with pytest.raises(ValueError):
        make_snapshot(b2, root2)


def test_too_large_file_rejected(tmp_path):
    b, root, file = fixture_for(tmp_path)
    with file.open('wb') as dest:
        dest.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match='exceeds size cap'):
        make_snapshot(b, root)


def test_no_evidence_rejected(tmp_path):
    b = original().model_dump(mode='json')
    b['evidence'] = []
    for x in b['observations']:
        if x['certainty'] == 'observed':
            x['certainty'] = 'inferred'
        x['evidence_ids'] = []
    with pytest.raises(ValueError, match='no evidence'):
        make_snapshot(ObservationBundle.model_validate(b), tmp_path)


def test_cli_snapshot_and_verify_readonly(capsys):
    assert main(['snapshot', str(FIXTURE), str(ROOT)]) == 0
    obj = json.loads(capsys.readouterr().out)
    assert obj == json.loads(GOLDEN.read_text())
    assert main(['verify', str(FIXTURE), str(ROOT), str(GOLDEN)]) == 0
    audit = json.loads(capsys.readouterr().out)
    assert audit['bytes_matching'] == 1
    assert audit['approval_granted'] is False


def test_cli_errors_fail_closed(tmp_path,capsys):
    other = tmp_path/'none.json'
    assert main(['verify',str(FIXTURE),str(ROOT),str(other)]) == 1
    result=capsys.readouterr()
    assert result.out == '' and result.err.startswith('FAIL:')


def test_no_network_or_file_write_in_audit_source():
    src=(ROOT/'astra_contracts/evidence_integrity.py').read_text(encoding='utf-8')
    for pattern in ('requests.get(', 'urllib.request', 'playwright', 'subprocess.run(',
                    '.write_text(', '.write_bytes(', 'httpx.get(', 'httpx.post('):
        assert pattern not in src
