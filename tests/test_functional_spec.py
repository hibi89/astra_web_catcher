"""Generic, no-network evidence-to-spec tests for ASTRA Step 4-B."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.functional_spec import FunctionalSpecDraft, derive_spec, main
from astra_contracts.observation import ObservationBundle

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / 'fixtures/jp_nail_brand_filter_observation_20261018.json'
SYNTHETIC = ROOT / 'fixtures/observation_brand_filter.json'


def bundle(path=REAL):
    return ObservationBundle.model_validate_json(path.read_text(encoding='utf-8'))


def test_archived_case_has_one_review_candidate_and_two_unresolved():
    spec = derive_spec(bundle())
    assert spec.schema_version == '0.1'
    assert len(spec.candidate_features) == 1
    assert len(spec.unresolved) == 2
    f = spec.candidate_features[0]
    assert f.feature.value == 'filter'
    assert f.evidence_quality.value == 'archived_secondary'
    assert f.evidence[0].source_ref == 'evidence/jp_nail_brand_filter_source_20261018.md'
    assert f.recorded_action is None  # original click trace not recorded
    assert {x.reason for x in spec.unresolved} == {'unknown'}


def test_null_and_zero_preserved_exactly():
    spec = derive_spec(bundle())
    fields = {f.field: f for f in spec.candidate_features[0].changed_fields}
    assert fields['direct_application_posts'].before == 71
    assert fields['direct_application_posts'].after == 0
    assert fields['selected_brand'].before == 'ALL'
    assert fields['selected_brand'].after == 'OHORA'
    assert 'report_run_number' not in fields  # 3728 unchanged, no invented event
    assert all('original' not in x.field for x in fields.values())
    assert 'original_ratio_formula' in spec.unresolved[1].mentioned_fields


def test_generating_twice_yields_identical_json():
    obj = bundle()
    a = derive_spec(obj).model_dump_json()
    b = derive_spec(obj).model_dump_json()
    assert a == b
    assert len(derive_spec(obj).source_sha256) == 64


def test_candidate_is_always_review_gated_and_no_mapping():
    spec = derive_spec(bundle())
    assert spec.status == 'draft_requires_review'
    assert not spec.implementation_ready
    assert spec.db_api_mapping_status == 'not_started'
    assert all(f.review_status == 'requires_review' for f in spec.candidate_features)
    assert all(g.status == 'pending' for g in spec.approval_gates)
    assert {g.key for g in spec.approval_gates} == {
        'confirm_behavior', 'approve_db_api_mapping', 'confirm_metric_formulas',
        'authorize_external_or_write_actions'
    }


def test_inferred_never_becomes_an_approved_feature():
    data = bundle(SYNTHETIC).model_dump(mode='json')
    data['observations'][0]['certainty'] = 'inferred'
    data['observations'][0]['evidence_ids'] = []
    spec = derive_spec(ObservationBundle.model_validate(data))
    assert len(spec.candidate_features) == 0
    assert spec.unresolved[0].reason == 'inferred'
    assert not spec.implementation_ready


def test_unknown_only_bundle_no_candidate():
    data = bundle().model_dump(mode='json')
    data['observations'] = data['observations'][1:]
    spec = derive_spec(ObservationBundle.model_validate(data))
    assert spec.candidate_features == []
    assert len(spec.unresolved) == 2
    assert spec.db_api_mapping_status == 'not_started'


def test_direct_screenshot_record_is_not_misclassified_as_archived():
    spec = derive_spec(bundle(SYNTHETIC))
    assert spec.candidate_features[0].evidence_quality.value == 'reported_direct_not_independently_verified'
    assert len(spec.candidate_features[0].evidence) == 2


def test_invalid_foreign_evidence_ref_rejected_before_generation():
    data = bundle().model_dump(mode='json')
    data['observations'][0]['evidence_ids'] = ['missing']
    with pytest.raises(ValidationError):
        derive_spec(ObservationBundle.model_validate(data))


def test_unknown_evidence_cannot_be_promoted():
    data = bundle().model_dump(mode='json')
    data['observations'][1]['certainty'] = 'observed'
    with pytest.raises(ValidationError):
        derive_spec(ObservationBundle.model_validate(data))


@pytest.mark.parametrize('field,value', [
    ('implementation_ready', True),
    ('status', 'approved'),
    ('db_api_mapping_status', 'mapped'),
])
def test_output_model_rejects_approval_tampering(field, value):
    data = derive_spec(bundle()).model_dump(mode='json')
    data[field] = value
    with pytest.raises(ValidationError):
        FunctionalSpecDraft.model_validate(data)


def test_output_model_rejects_feature_approval_tampering():
    data = derive_spec(bundle()).model_dump(mode='json')
    data['candidate_features'][0]['review_status'] = 'approved'
    with pytest.raises(ValidationError):
        FunctionalSpecDraft.model_validate(data)


def test_output_model_rejects_gate_approval_tampering():
    data = derive_spec(bundle()).model_dump(mode='json')
    data['approval_gates'][0]['status'] = 'approved'
    with pytest.raises(ValidationError):
        FunctionalSpecDraft.model_validate(data)


def test_cli_stdout_roundtrip_without_creating_output(tmp_path, capsys):
    assert main([str(REAL)]) == 0
    captured = capsys.readouterr()
    obj = FunctionalSpecDraft.model_validate_json(captured.out)
    assert len(obj.candidate_features) == 1
    assert captured.err == ''
    assert list(tmp_path.iterdir()) == []


def test_cli_invalid_file_nonzero_and_no_json_stdout(tmp_path, capsys):
    invalid = tmp_path / 'invalid.json'
    invalid.write_text('{"schema_version":"0.1"}', encoding='utf-8')
    assert main([str(invalid)]) == 1
    out = capsys.readouterr()
    assert out.out == ''
    assert 'FAIL:' in out.err


def test_code_has_no_network_db_or_external_execution_imports():
    source = (ROOT / 'astra_contracts' / 'functional_spec.py').read_text(encoding='utf-8')
    for forbidden in ['import requests', 'import sqlite3', 'import subprocess', 'import urllib.request', 'import socket', 'from openai', 'import os']:
        assert forbidden not in source


def test_cross_feature_candidate_is_generic_not_nail_hardcoded():
    data = bundle(SYNTHETIC).model_dump(mode='json')
    data['site_url'] = 'https://example.com/jobs'
    data['observations'][0]['feature'] = 'search'
    data['observations'][0]['title'] = 'Job results change with query'
    data['observations'][0]['claim'] = 'The displayed result count changes for a query.'
    data['observations'][0]['before'] = {'query': '', 'count': 20}
    data['observations'][0]['after'] = {'query': 'data', 'count': 5}
    spec = derive_spec(ObservationBundle.model_validate(data))
    assert spec.candidate_features[0].feature.value == 'search'
    assert {x.field for x in spec.candidate_features[0].changed_fields} == {'query','count'}
    assert spec.site_url == 'https://example.com/jobs'


def test_checked_in_golden_example_matches_generator():
    golden = ROOT / 'fixtures/jp_nail_functional_spec_draft_20261018.json'
    generated = derive_spec(bundle()).model_dump(mode='json')
    assert json.loads(golden.read_text(encoding='utf-8')) == generated
