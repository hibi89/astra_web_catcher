"""Offline traceability should be review-only even for 'observed' operator claims."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.observed_ui_mapping import (
    UIActionMappingPlan, build_ui_mapping,
)
from astra_contracts.schema_query_extension import create_query_app
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'fixtures'


def cases(kind='products'):
    stem = f'synthetic_ui_mapping_{kind}_20261019'
    b = ObservationBundle.model_validate_json((FIX / (stem + '_observation.json')).read_text())
    d = OwnedSchemaDeclaration.model_validate_json((FIX / (stem + '_schema.json')).read_text())
    t = AlternateSyntheticTable.model_validate_json((FIX / f'synthetic_reuse_{kind}_table_20261019.json').read_text())
    p = UIActionMappingPlan.model_validate_json((FIX / (stem + '_plan.json')).read_text())
    return b, d, t, p


def updated(bundle, decl, table, plan):
    p = plan.model_dump(mode='json')
    p['observation_sha256'] = fingerprint(bundle)
    p['declaration_sha256'] = fingerprint(decl)
    p['synthetic_table_sha256'] = fingerprint(table)
    return UIActionMappingPlan.model_validate(p)


@pytest.mark.parametrize('kind,expected_field,expected_value,expected_count', [
    ('products', 'family', 'colors', 2), ('tickets', 'lane', 'Open', 3),
])
def test_positive_demonstrations_never_approved(kind, expected_field, expected_value, expected_count):
    b, d, t, p = cases(kind)
    report = build_ui_mapping(b, d, t, p, FIX)
    assert report.status == 'review_only_never_authorized'
    assert report.evidence_integrity_verified is True
    assert report.evidence_content_authenticated is False
    assert report.original_site_behavior_verified is False
    assert report.owner_db_accessed is False
    assert report.generation_authorized is False
    assert report.production_ready is False
    assert report.findings[0].status == 'synthetic_preview_candidate_unapproved'
    c = report.synthetic_preview_candidates[0]
    assert c.query_filter_by == expected_field
    assert c.query_filter_value == expected_value
    assert c.demo_match_count == expected_count
    assert c.semantics_approved is False and c.synthetic_illustration_only is True
    sort_field = next(x.source_field for x in t.bindings if x.logical_field == 'id')
    with TestClient(create_query_app(t)) as client:
        resp = client.get(c.read_only_route, params={'sort_by': sort_field, 'direction': 'asc',
                            'filter_by': c.query_filter_by, 'filter_value': c.query_filter_value})
        assert resp.status_code == 200
        assert len(resp.json()['items']) == expected_count
        assert resp.json()['original_site_behavior_verified'] is False


def test_archived_real_site_claim_not_upgraded():
    b = ObservationBundle.model_validate_json((FIX / 'jp_nail_brand_filter_observation_20261018.json').read_text())
    d = OwnedSchemaDeclaration.model_validate_json((FIX / 'synthetic_owned_schema_mapping_20261018.json').read_text())
    t = cases()[2]
    p = UIActionMappingPlan.model_validate_json((FIX / 'synthetic_ui_mapping_archive_blocked_plan_20261019.json').read_text())
    report = build_ui_mapping(b, d, t, p, ROOT)
    assert report.findings[0].status == 'archived_secondary_only'
    assert report.synthetic_preview_candidates == []
    assert sorted(report.unresolved_observation_ids) == ['filter_execution_unknown','ratio_formula_unknown']


@pytest.mark.parametrize('field', ['observation_sha256', 'declaration_sha256', 'synthetic_table_sha256'])
def test_reject_stale_input_sha(field):
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw[field] = '0' * 64
    with pytest.raises(ValueError, match='stale or unrelated'):
        build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)


def test_reject_stale_evidence_digest():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    evidence_key = next(iter(raw['evidence_sha256_by_id']))
    raw['evidence_sha256_by_id'][evidence_key] = 'f'*64
    with pytest.raises(ValueError, match='evidence integrity'):
        build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)


def test_evidence_bytes_edited_are_detected(tmp_path):
    b, d, t, p = cases()
    relative = Path(b.evidence[0].source_ref)
    copy = tmp_path / relative
    copy.parent.mkdir(parents=True)
    copy.write_bytes((FIX / relative).read_bytes() + b'attack')
    with pytest.raises(ValueError, match='evidence integrity'):
        build_ui_mapping(b, d, t, p, tmp_path)


def test_evidence_symlink_rejected(tmp_path):
    b, d, t, p = cases()
    relative = Path(b.evidence[0].source_ref)
    link = tmp_path / relative
    link.parent.mkdir(parents=True)
    link.symlink_to(FIX / relative)
    with pytest.raises(ValueError, match='symlink'):
        build_ui_mapping(b, d, t, p, tmp_path)


def test_missing_evidence_reference_rejected(tmp_path):
    b, d, t, p = cases()
    with pytest.raises(ValueError, match='missing'):
        build_ui_mapping(b, d, t, p, tmp_path)


def test_evidence_id_set_requires_exactness():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw['evidence_sha256_by_id']['extra_key'] = '1' * 64
    with pytest.raises(ValueError, match='cover exactly'):
        build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)


@pytest.mark.parametrize('authority', ['original_site_verified', 'owner_database_access_authorized',
                                       'production_generation_authorized', 'review_approved'])
def test_cannot_forge_authority(authority):
    raw = cases()[3].model_dump(mode='json')
    raw[authority] = True
    with pytest.raises(ValidationError):
        UIActionMappingPlan.model_validate(raw)


def test_unknown_reference_observation_blocked():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['certainty'] = 'unknown'
    raw['observations'][0]['evidence_ids'] = []
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'unknown_or_inferred_observation'
    assert report.synthetic_preview_candidates == []


def test_inferred_reference_observation_blocked():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['certainty'] = 'inferred'
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'unknown_or_inferred_observation'


def test_only_filter_features_supported():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['feature'] = 'create'
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'unsupported_observed_feature'


def test_missing_action_trace_blocked():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['action'] = None
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'missing_action_trace'


def test_unchanged_field_blocked():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['after']['selected_category'] = 'ALL'
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'ui_field_not_observed_as_changed'


def test_bad_binding_claim_blocked():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw['links'][0]['resource_field'] = 'count'
    report = build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)
    assert report.findings[0].status == 'explicit_source_binding_mismatch'


def test_declared_type_conflict_blocked():
    b, d, t, p = cases()
    raw = d.model_dump(mode='json')
    raw['resources'][0]['fields'][0]['data_type'] = 'integer'
    d2 = OwnedSchemaDeclaration.model_validate(raw)
    report = build_ui_mapping(b, d2, t, updated(b,d2,t,p), FIX)
    assert report.findings[0].status == 'source_mapping_not_compatible'


def test_preview_field_missing_blocked():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw['links'][0]['synthetic_preview_field'] = 'invented_column'
    report = build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)
    assert report.findings[0].status == 'preview_field_not_declared'


def test_preview_column_wrong_type_blocked():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw['links'][0]['synthetic_preview_field'] = 'popularity'
    report = build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)
    assert report.findings[0].status == 'preview_type_conflict'


def test_preview_value_mismatch_blocked():
    b, d, t, p = cases()
    raw = b.model_dump(mode='json')
    raw['observations'][0]['after']['selected_category'] = 'unknown_category'
    b2 = ObservationBundle.model_validate(raw)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'observed_value_not_in_preview'


def test_nonexistent_source_observation_rejected():
    b, d, t, p = cases()
    raw = p.model_dump(mode='json')
    raw['links'][0]['observation_id'] = 'not_real'
    with pytest.raises(ValueError, match='nonexistent observation'):
        build_ui_mapping(b, d, t, UIActionMappingPlan.model_validate(raw), FIX)


@pytest.mark.parametrize('field,value', [('resource_field','id; DROP TABLE'),('synthetic_preview_field','family;--'),('ui_field','../../password')])
def test_injection_identifiers_rejected(field,value):
    raw = cases()[3].model_dump(mode='json')
    raw['links'][0][field] = value
    with pytest.raises(ValidationError):
        UIActionMappingPlan.model_validate(raw)


def test_no_duplicate_links_and_unknown_fields():
    raw = cases()[3].model_dump(mode='json')
    raw['links'].append(copy.deepcopy(raw['links'][0]))
    with pytest.raises(ValidationError):
        UIActionMappingPlan.model_validate(raw)
    raw = cases()[3].model_dump(mode='json')
    raw['links'][0]['forged_admin_override'] = True
    with pytest.raises(ValidationError):
        UIActionMappingPlan.model_validate(raw)


def test_no_files_written_or_arguments_mutated(tmp_path):
    b, d, t, p = cases()
    before = [fingerprint(x) for x in (b,d,t,p)]
    files_before = sorted(p.name for p in tmp_path.iterdir())
    a = build_ui_mapping(b,d,t,p,FIX)
    z = build_ui_mapping(b,d,t,p,FIX)
    assert a.model_dump(mode='json') == z.model_dump(mode='json')
    assert [fingerprint(x) for x in (b,d,t,p)] == before
    assert [p.name for p in tmp_path.iterdir()] == files_before


def test_cli_stdout_only_and_invalid_exit():
    stem='synthetic_ui_mapping_products_20261019'
    args=[str(FIX / (stem+'_observation.json')), str(FIX / (stem+'_schema.json')),
          str(FIX/'synthetic_reuse_products_table_20261019.json'),str(FIX/(stem+'_plan.json')),str(FIX)]
    success=subprocess.run([sys.executable,'-m','astra_contracts.observed_ui_mapping',*args], cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert success.returncode==0, success.stderr
    body=json.loads(success.stdout)
    assert body['status']=='review_only_never_authorized'
    assert len(body['synthetic_preview_candidates']) == 1
    failure=subprocess.run([sys.executable,'-m','astra_contracts.observed_ui_mapping',*args[:-1],str(ROOT/'not-a-root')], cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert failure.returncode != 0 and failure.stdout == ''


def test_archive_note_digest_is_pinned():
    b = ObservationBundle.model_validate_json((FIX / 'jp_nail_brand_filter_observation_20261018.json').read_text())
    p = UIActionMappingPlan.model_validate_json((FIX / 'synthetic_ui_mapping_archive_blocked_plan_20261019.json').read_text())
    sha=hashlib.sha256((ROOT / b.evidence[0].source_ref).read_bytes()).hexdigest()
    assert sha == p.evidence_sha256_by_id[b.evidence[0].id]


def test_explicit_integer_filter_contract_uses_strict_numeric_value():
    b, d, t, p = cases()
    obs = b.model_dump(mode='json')
    obs['observations'][0]['after']['visible_count'] = 90
    b2 = ObservationBundle.model_validate(obs)
    pl = p.model_dump(mode='json')
    pl['links'][0].update(ui_field='visible_count', resource_field='count',
                          synthetic_preview_field='popularity')
    plan = updated(b2, d, t, UIActionMappingPlan.model_validate(pl))
    report = build_ui_mapping(b2, d, t, plan, FIX)
    candidate = report.synthetic_preview_candidates[0]
    assert candidate.query_filter_value == 90
    assert type(candidate.query_filter_value) is int
    assert candidate.demo_match_count == 1
    with TestClient(create_query_app(t)) as client:
        response = client.get('/api/rows',params={'sort_by':'sku','filter_by':'popularity','filter_value':90})
        assert response.status_code == 200
        assert [x['sku'] for x in response.json()['items']] == ['prod-cobalt']


def test_boolean_cannot_impersonate_numeric_ui_field():
    b, d, t, p = cases()
    obs = b.model_dump(mode='json')
    obs['observations'][0]['after']['visible_count'] = True
    b2 = ObservationBundle.model_validate(obs)
    pl = p.model_dump(mode='json')
    pl['links'][0].update(ui_field='visible_count', resource_field='count',
                          synthetic_preview_field='popularity')
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,UIActionMappingPlan.model_validate(pl)), FIX)
    assert report.findings[0].status == 'source_mapping_not_compatible'
    assert report.synthetic_preview_candidates == []


def test_string_case_not_inferred_as_equivalent():
    b, d, t, p = cases()
    obs = b.model_dump(mode='json')
    obs['observations'][0]['after']['selected_category'] = 'COLORS'
    b2 = ObservationBundle.model_validate(obs)
    report = build_ui_mapping(b2, d, t, updated(b2,d,t,p), FIX)
    assert report.findings[0].status == 'observed_value_not_in_preview'


def test_owner_supplied_declaration_refused_even_when_hash_matches():
    b, d, t, p = cases()
    decl = d.model_dump(mode='json')
    decl['source_kind'] = 'owner_supplied_document'
    d2 = OwnedSchemaDeclaration.model_validate(decl)
    with pytest.raises(ValueError, match='owner-supplied or live'):
        build_ui_mapping(b, d2, t, updated(b,d2,t,p), FIX)


def test_evidence_root_symlink_refused(tmp_path):
    b, d, t, p = cases()
    link = tmp_path / 'linked_root'
    link.symlink_to(FIX, target_is_directory=True)
    with pytest.raises(ValueError, match='real directory'):
        build_ui_mapping(b,d,t,p,link)


def test_evidence_root_is_a_file_refused(tmp_path):
    b, d, t, p = cases()
    file = tmp_path / 'not_a_directory'
    file.write_text('test')
    with pytest.raises(ValueError, match='real directory'):
        build_ui_mapping(b,d,t,p,file)


@pytest.mark.parametrize('kind', ['products', 'tickets'])
def test_checked_in_report_is_exactly_reproducible(kind):
    b,d,t,p=cases(kind)
    expected=json.loads((FIX/f'synthetic_ui_mapping_{kind}_report_20261019.json').read_text())
    actual=build_ui_mapping(b,d,t,p,FIX).model_dump(mode='json')
    assert actual == expected


def test_checked_in_archived_blocked_report_is_exactly_reproducible():
    b=ObservationBundle.model_validate_json((FIX/'jp_nail_brand_filter_observation_20261018.json').read_text())
    d=OwnedSchemaDeclaration.model_validate_json((FIX/'synthetic_owned_schema_mapping_20261018.json').read_text())
    t=cases()[2]
    p=UIActionMappingPlan.model_validate_json((FIX/'synthetic_ui_mapping_archive_blocked_plan_20261019.json').read_text())
    expected=json.loads((FIX/'synthetic_ui_mapping_archive_report_20261019.json').read_text())
    assert build_ui_mapping(b,d,t,p,ROOT).model_dump(mode='json') == expected
