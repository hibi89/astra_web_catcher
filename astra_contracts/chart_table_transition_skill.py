"""Review-only chart/table mechanism from ONE pinned, verified public OWID capture.

Read-only local ZIP analysis. No URL access, DB mapping, code generation, or approval.
Command: python -m astra_contracts.chart_table_transition_skill --archive <downloaded-artifact.zip>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

PROOF_RUN = 39211418515
PROOF_ARTIFACT = 12168150702
PROOF_ZIP_SHA256 = '6ad5f561b78271be7da3b4efb8e61fcc1a6c269b4ebf8a26e1b32c23b81717e6'
SOURCE_URL = 'https://ourworldindata.org/grapher/life-expectancy?tab=chart'
ACTION = 'Select the Table view on a public life-expectancy dashboard'
OBSERVATION_ID = 'public_table_view'
SCREENSHOTS = {
    'before': ('captures/before.png', 159304, 'd94cf65cb9850f2546b078759214414b70ad7f277e5200970d76489fe6df8c60'),
    'after': ('captures/after.png', 122367, '4abdc085d07cfa0397e3a626eab23974d28107becb680dfdcdf7f1ab60a5e6dc'),
}
MEMBERS = {'bundle.json', 'request.json', 'intake_manifest.json', 'result.json',
           *(details[0] for details in SCREENSHOTS.values())}
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024
FALSE_FLAGS = ('original_site_behavior_verified', 'screenshot_authenticity_verified',
               'formula_verified', 'user_approval_verified', 'code_generation_authorized',
               'database_access_authorized', 'deployment_authorized')


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def _parse_json(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode('utf-8'))
    _require(type(value) is dict, 'JSON top-level must be an object')
    return value


def _canonical_digest(model: dict[str, Any]) -> str:
    """Existing Pydantic fingerprint convention: sorted compact JSON, UTF-8."""
    data = json.dumps(model, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def _load_zip(raw: bytes) -> dict[str, bytes]:
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            items = z.infolist()
            _require(len(items) == len(MEMBERS), 'unexpected archive member count')
            _require({i.filename for i in items} == MEMBERS, 'unexpected archive member names')
            files = {}
            for item in items:
                _require(not item.is_dir(), 'archive directories forbidden')
                _require(item.file_size <= MAX_MEMBER_BYTES, 'oversized archive member')
                _require(not (item.external_attr >> 16) & 0o170000 == 0o120000,
                         'archive symlink forbidden')
                value = z.read(item)
                _require(len(value) == item.file_size, 'archive member length mismatch')
                files[item.filename] = value
            return files
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ValueError('invalid ZIP archive') from exc


def _validate_evidence(raw: bytes, *, expected_zip_sha256: str) -> dict[str, Any]:
    """Validate archived bytes, their recorded links and the exact observed UI claim.

    expected_zip_sha256 is supplied by the single public wrapper; tests use a
    substitute digest solely to exercise structural fail-closed cases.
    """
    _require(len(raw) <= MAX_ARCHIVE_BYTES, 'oversized ZIP')
    _require(re.fullmatch(r'[0-9a-f]{64}', expected_zip_sha256) is not None,
             'invalid pinned digest')
    _require(hashlib.sha256(raw).hexdigest() == expected_zip_sha256, 'pinned ZIP SHA mismatch')
    files = _load_zip(raw)
    bundle = _parse_json(files['bundle.json'])
    request = _parse_json(files['request.json'])
    manifest = _parse_json(files['intake_manifest.json'])
    result = _parse_json(files['result.json'])
    _require(bundle.get('schema_version') == '1.0' and bundle.get('site_url') == SOURCE_URL,
             'wrong observation source')
    observations = bundle.get('observations')
    _require(type(observations) is list and len(observations) == 1,
             'unexpected observations')
    obs = observations[0]
    _require(type(obs) is dict and obs.get('id') == OBSERVATION_ID
             and obs.get('feature') == 'list' and obs.get('certainty') == 'inferred'
             and obs.get('evidence_ids') == [] and obs.get('action') == ACTION,
             'observation identity or certainty changed')
    _require(obs.get('before') == {'view': 'chart', 'visible_table_rows': 0}
             and obs.get('after') == {'view': 'table', 'visible_table_rows': 265},
             'view transition does not match pinned evidence')
    _require(request.get('source_kind') == 'manually_supplied_local_files'
             and request.get('version') == '0.1'
             and request.get('observation_sha256') == _canonical_digest(bundle),
             'observation/request fingerprint mismatch')
    _require(manifest.get('version') == '0.1'
             and manifest.get('status') == 'pending_manual_evidence_review'
             and manifest.get('original_bundle_sha256') == _canonical_digest(bundle)
             and manifest.get('request_sha256') == _canonical_digest(request)
             and manifest.get('source_bundle_unchanged') is True,
             'intake manifest fingerprint or status mismatch')
    _require(all(manifest.get(key) is False for key in FALSE_FLAGS),
             'archive cannot assert review, access or generation approval')
    entries = manifest.get('entries')
    captures = request.get('captures')
    _require(type(entries) is list and len(entries) == 2
             and type(captures) is list and len(captures) == 2,
             'exactly two screenshot evidence entries required')
    indexed = {}
    for entry in entries:
        _require(type(entry) is dict and type(entry.get('evidence')) is dict,
                 'malformed capture manifest entry')
        evidence_id = entry['evidence'].get('id')
        _require(evidence_id in SCREENSHOTS and evidence_id not in indexed,
                 'unexpected or duplicate evidence ID')
        path, length, digest = SCREENSHOTS[evidence_id]
        _require(entry.get('stored_ref') == path and entry['evidence'].get('source_ref') == path
                 and entry['evidence'].get('kind') == 'screenshot'
                 and entry.get('proposal_observation_ids') == [OBSERVATION_ID]
                 and entry.get('source_claim') == 'unverified_operator_supplied'
                 and entry.get('behavior_claim_upgraded') is False,
                 'capture reference or provenance relabeled')
        _require(entry.get('size_bytes') == length and entry.get('sha256') == digest
                 and len(files[path]) == length
                 and hashlib.sha256(files[path]).hexdigest() == digest
                 and files[path].startswith(b'\x89PNG\r\n\x1a\n'),
                 'pinned screenshot integrity mismatch')
        indexed[evidence_id] = entry['evidence'].get('captured_at')
    for capture in captures:
        _require(type(capture) is dict and type(capture.get('evidence')) is dict,
                 'malformed intake request capture')
        ev = capture['evidence']
        _require(ev.get('id') in indexed and capture.get('observation_ids') == [OBSERVATION_ID]
                 and ev.get('source_ref') == SCREENSHOTS[ev['id']][0]
                 and ev.get('captured_at') == indexed[ev['id']],
                 'capture request/manifest links mismatch')
    _require(indexed['before'] == '2026-10-19T06:42:28.513725Z'
             and indexed['after'] == '2026-10-19T06:42:29.202048Z',
             'unexpected capture timestamps')
    _require(result.get('status') == 'public_dashboard_capture_review_pending'
             and result.get('public_source') == SOURCE_URL
             and result.get('action') == ACTION
             and type(result.get('before_table_rows')) is int and result['before_table_rows'] == 0
             and type(result.get('after_table_rows')) is int and result['after_table_rows'] == 265
             and type(result.get('matched_screenshots')) is int and result['matched_screenshots'] == 2,
             'browser result does not match pinned UI state')
    _require(all(result.get(k) is False for k in ('original_site_behavior_verified',
             'customer_schema_connected', 'generation_authorized', 'deployment_authorized')),
             'browser result cannot authorize or upgrade claims')
    return {'observation_id': obs['id'], 'evidence_ids': sorted(indexed),
            'before_table_rows': 0, 'after_table_rows': 265}


def review_pinned_artifact(path: Path) -> dict[str, Any]:
    """The only public validation entry: exact GitHub-run archived ZIP required."""
    path = Path(path)
    _require(not path.is_symlink() and path.is_file(), 'regular ZIP file required')
    _require(path.stat().st_size <= MAX_ARCHIVE_BYTES, 'oversized ZIP')
    evidence = _validate_evidence(path.read_bytes(), expected_zip_sha256=PROOF_ZIP_SHA256)
    return {
        'skill_version': '0.1', 'skill_id': 'chart_table_mode_switch',
        'status': 'review_only_source_semantics_unapproved',
        'source_url': SOURCE_URL,
        'github_run_id': PROOF_RUN, 'github_artifact_id': PROOF_ARTIFACT,
        'archive_sha256': PROOF_ZIP_SHA256,
        'observation_id': evidence['observation_id'],
        'evidence_ids': evidence['evidence_ids'],
        'screen_sha256_by_id': {key: value[2] for key, value in SCREENSHOTS.items()},
        'trigger': 'click_visible_table_control',
        'before': {'view': 'chart', 'visible_table_rows': evidence['before_table_rows']},
        'after': {'view': 'table', 'visible_table_rows': evidence['after_table_rows']},
        'mechanism_proposal': 'Render one dataset in chart or table mode using local UI state; implementation details are not inferred',
        'source_behavior_certainty': 'inferred',
        'back_end_implementation_known': False,
        'table_sorting_verified': False,
        'source_formulas_verified': False,
        'same_dataset_semantics_verified': False,
        'owner_schema_connected': False,
        'owner_approved_field_bindings': [],
        'required_owned_schema_fields': ['entity_identifier', 'time_period', 'numeric_measure', 'aggregation_semantics'],
        'unresolved': ['owner_schema_not_provided', 'field_semantics_unmapped',
                       'metric_formula_unknown', 'reference_mechanism_internal_unknown'],
        'screenshot_bytes_match_pinned_archive': True,
        'screenshot_authenticity_independently_verified': False,
        'operator_review_approved': False,
        'code_generation_authorized': False,
        'customer_db_access_authorized': False,
        'deployment_authorized': False,
        'network_used': False, 'files_written': False,
        'generation_contract': 'blocked_pending_review',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline review-only OWID chart/table mechanism skill')
    parser.add_argument('--archive', type=Path, help='Locally downloaded exact GitHub artifact ZIP')
    args = parser.parse_args(argv)
    if args.archive is None:
        print(json.dumps({'skill_id': 'chart_table_mode_switch', 'mode': 'dry_run',
                          'archive_required': True, 'network_used': False,
                          'files_written': False, 'generation_contract': 'blocked_pending_review'}))
        return 0
    try:
        result = review_pinned_artifact(args.archive)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
