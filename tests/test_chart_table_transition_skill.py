"""Fail-closed tests: pinned evidence, tampering, and approval boundaries."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from astra_contracts.chart_table_transition_skill import (
    PROOF_ZIP_SHA256, SCREENSHOTS, _validate_evidence, main, review_pinned_artifact,
)


def _archive(entries: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for key, value in entries.items():
            z.writestr(key, value)
    return out.getvalue()


def _sample() -> dict[str, bytes]:
    """Small structural fixture. Not the pinned GitHub evidence."""
    from astra_contracts.chart_table_transition_skill import ACTION, SOURCE_URL, OBSERVATION_ID, _canonical_digest
    bundle = {'schema_version': '1.0', 'site_url': SOURCE_URL,
              'observations': [{'id': OBSERVATION_ID, 'feature': 'list',
                                'certainty': 'inferred', 'evidence_ids': [], 'action': ACTION,
                                'before': {'view': 'chart', 'visible_table_rows': 0},
                                'after': {'view': 'table', 'visible_table_rows': 265}}]}
    req = {'version': '0.1', 'source_kind': 'manually_supplied_local_files',
           'observation_sha256': _canonical_digest(bundle), 'captures': []}
    manifest = {'version': '0.1', 'status': 'pending_manual_evidence_review',
                'original_bundle_sha256': _canonical_digest(bundle),
                'request_sha256': _canonical_digest(req), 'source_bundle_unchanged': True,
                'entries': [], **{key: False for key in (
                    'original_site_behavior_verified', 'screenshot_authenticity_verified',
                    'formula_verified', 'user_approval_verified', 'code_generation_authorized',
                    'database_access_authorized', 'deployment_authorized')}}
    for key, (filename, length, digest) in SCREENSHOTS.items():
        ev = {'id': key, 'kind': 'screenshot', 'source_ref': filename,
              'captured_at': '2026-10-19T06:42:28.513725Z' if key == 'before' else '2026-10-19T06:42:29.202048Z'}
        req['captures'].append({'evidence': ev, 'observation_ids': [OBSERVATION_ID]})
        manifest['entries'].append({'evidence': ev, 'stored_ref': filename,
                                    'proposal_observation_ids': [OBSERVATION_ID],
                                    'size_bytes': length, 'sha256': digest,
                                    'source_claim': 'unverified_operator_supplied',
                                    'behavior_claim_upgraded': False})
    manifest['request_sha256'] = _canonical_digest(req)
    result = {'status': 'public_dashboard_capture_review_pending',
              'public_source': SOURCE_URL, 'action': ACTION,
              'before_table_rows': 0, 'after_table_rows': 265, 'matched_screenshots': 2,
              **{key: False for key in ('original_site_behavior_verified',
                  'customer_schema_connected', 'generation_authorized', 'deployment_authorized')}}
    return {**{name: json.dumps(obj).encode() for name, obj in (
                ('bundle.json', bundle), ('request.json', req),
                ('intake_manifest.json', manifest), ('result.json', result))},
            **{filename: b'\x89PNG\r\n\x1a\n' + bytes(length - 8)
               for filename, length, _ in SCREENSHOTS.values()}}


def test_dry_run_no_external_access(capsys):
    assert main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['archive_required'] and not result['network_used'] and not result['files_written']


def test_missing_archive_fails(tmp_path, capsys):
    assert main(['--archive', str(tmp_path / 'missing.zip')]) == 1
    assert 'FAIL:' in capsys.readouterr().err


def test_tampered_zip_fails_even_when_structural_contents_sensible(tmp_path):
    archive = _archive(_sample())
    p = tmp_path / 'fake.zip'
    p.write_bytes(archive)
    with pytest.raises(ValueError, match='pinned ZIP SHA mismatch'):
        review_pinned_artifact(p)
    assert hashlib.sha256(archive).hexdigest() != PROOF_ZIP_SHA256


def test_archive_symlink_rejected(tmp_path):
    archive = tmp_path / 'archive.zip'
    archive.write_bytes(_archive(_sample()))
    link = tmp_path / 'alias.zip'
    try:
        link.symlink_to(archive)
    except OSError:
        pytest.skip('symlinks unavailable')
    with pytest.raises(ValueError, match='regular ZIP file required'):
        review_pinned_artifact(link)


def test_structural_pin_blocks_fabricated_png():
    raw = _archive(_sample())
    with pytest.raises(ValueError, match='pinned screenshot integrity mismatch'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())


def test_fake_approval_refused_before_image_bytes():
    sample = _sample()
    manifest = json.loads(sample['intake_manifest.json'])
    manifest['code_generation_authorized'] = True
    sample['intake_manifest.json'] = json.dumps(manifest).encode()
    raw = _archive(sample)
    with pytest.raises(ValueError, match='cannot assert review'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())


def test_fake_source_view_transition_refused():
    sample = _sample()
    bundle = json.loads(sample['bundle.json'])
    bundle['observations'][0]['after']['visible_table_rows'] = 264
    sample['bundle.json'] = json.dumps(bundle).encode()
    raw = _archive(sample)
    with pytest.raises(ValueError, match='view transition'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())


def test_fake_certainty_promoted_refused():
    sample = _sample()
    bundle = json.loads(sample['bundle.json'])
    bundle['observations'][0]['certainty'] = 'observed'
    sample['bundle.json'] = json.dumps(bundle).encode()
    raw = _archive(sample)
    with pytest.raises(ValueError, match='certainty changed'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())


def test_unexpected_archive_member_refused():
    sample = _sample()
    sample['.env'] = b'unsafe'
    raw = _archive(sample)
    with pytest.raises(ValueError, match='member count'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())


def test_structural_good_screenshot_binary_but_digest_wrong():
    sample = _sample()
    before_path = SCREENSHOTS['before'][0]
    sample[before_path] = b'\x89PNG\r\n\x1a\n' + bytes(SCREENSHOTS['before'][1] - 8)
    raw = _archive(sample)
    with pytest.raises(ValueError, match='pinned screenshot integrity mismatch'):
        _validate_evidence(raw, expected_zip_sha256=hashlib.sha256(raw).hexdigest())
