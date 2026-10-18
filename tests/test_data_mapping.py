"""Contract and safety regression for offline owner-schema mapping diagnostics."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import (OwnedSchemaDeclaration, MappingReport,
                                          compare_mappings, main)
from astra_contracts.functional_spec import FunctionalSpecDraft

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'fixtures/jp_nail_functional_spec_draft_20261018.json'
SCHEMA = ROOT / 'fixtures/synthetic_owned_schema_mapping_20261018.json'
GOLDEN = ROOT / 'fixtures/synthetic_mapping_report_20261018.json'


def spec_data():
    return json.loads(SPEC.read_text(encoding='utf-8'))


def schema_data():
    return json.loads(SCHEMA.read_text(encoding='utf-8'))


def report(s=None, d=None):
    return compare_mappings(FunctionalSpecDraft.model_validate(s or spec_data()),
                            OwnedSchemaDeclaration.model_validate(d or schema_data()))


def test_synthetic_manifest_and_report_are_not_real_source_claims():
    obj = report()
    assert obj.declaration_source_kind == 'synthetic_fixture'
    assert 'SYNTHETIC ONLY' in obj.declaration_source_label
    assert obj.schema_verified_against_live_system is False
    assert obj.mapping_approved is False and obj.implementation_ready is False
    assert obj.status == 'review_only'


def test_all_changed_fields_reported_without_guessed_names():
    r = report()
    assert len(r.findings) == 10
    assert r.counts == {'structurally_compatible_unapproved':3,'unmapped':4,
                        'missing_resource':1,'missing_resource_field':1,
                        'type_conflict':1,'unknown_ui_type':0,'nullable_conflict':0}
    assert r.counts['unmapped'] == len([x for x in r.findings if x.status == 'unmapped'])
    assert sorted({x.ui_field for x in r.findings}) == sorted(
        f['field'] for f in spec_data()['candidate_features'][0]['changed_fields'])


def test_known_cases_are_classified_without_approval():
    r = {x.ui_field: x for x in report().findings}
    assert r['selected_brand'].status == 'structurally_compatible_unapproved'
    assert r['analyzed_posts'].status == 'structurally_compatible_unapproved'
    assert r['average_reactions_displayed'].status == 'type_conflict'
    assert r['reels_posts'].status == 'missing_resource'
    assert r['sheet_posts'].status == 'missing_resource_field'
    assert r['reported_reels_percent'].status == 'unmapped'
    assert r['direct_application_posts'].status == 'unmapped'
    assert r['analyzed_posts'].declared_type.value == 'integer'


def test_unresolved_metrics_stay_unresolved_with_approval_gates():
    r = report()
    assert r.unresolved_observation_ids == ['filter_execution_unknown','ratio_formula_unknown']
    assert len(r.approval_gates) == 7
    assert 'approve_db_api_mapping' in r.approval_gates
    assert 'confirm_metric_formulas' in r.approval_gates
    assert 'approve_any_source_changes' in r.approval_gates


def test_deterministic_sha_and_golden_json():
    one = report().model_dump(mode='json')
    two = report().model_dump(mode='json')
    assert one == two
    assert json.loads(GOLDEN.read_text(encoding='utf-8')) == one
    assert len(one['spec_source_sha256']) == 64
    assert len(one['declaration_sha256']) == 64


def test_false_approval_states_cannot_be_imported():
    x = report().model_dump(mode='json')
    for field in ('mapping_approved','schema_verified_against_live_system','implementation_ready'):
        y = copy.deepcopy(x)
        y[field] = True
        with pytest.raises(ValidationError):
            MappingReport.model_validate(y)


def test_unknown_binding_rejected_before_output():
    d = schema_data()
    d['bindings'][0]['ui_field'] = 'unrecorded_field'
    with pytest.raises(ValueError,match='nonexistent candidate'):
        report(d=d)


def test_duplicate_binding_rejected():
    d = schema_data()
    d['bindings'].append(copy.deepcopy(d['bindings'][0]))
    with pytest.raises(ValidationError,match='duplicate explicit mappings'):
        report(d=d)


def test_duplicate_resource_rejected():
    d = schema_data()
    d['resources'].append(copy.deepcopy(d['resources'][0]))
    with pytest.raises(ValidationError,match='duplicate resource IDs'):
        report(d=d)


def test_duplicate_resource_field_rejected():
    d = schema_data()
    d['resources'][0]['fields'].append(copy.deepcopy(d['resources'][0]['fields'][0]))
    with pytest.raises(ValidationError,match='duplicate field names'):
        report(d=d)


@pytest.mark.parametrize('bad_type',['blob','timestamp','object'])
def test_unlisted_type_rejected(bad_type):
    d = schema_data()
    d['resources'][0]['fields'][0]['data_type'] = bad_type
    with pytest.raises(ValidationError):
        report(d=d)


def test_null_is_distinct_from_zero_and_nullable_conflict():
    s = spec_data()
    field = next(f for f in s['candidate_features'][0]['changed_fields'] if f['field']=='analyzed_posts')
    field['after'] = None
    assert next(x for x in report(s=s).findings if x.ui_field=='analyzed_posts').status == 'nullable_conflict'
    d = schema_data()
    next(f for f in d['resources'][0]['fields'] if f['name']=='analyzed_total')['nullable']=True
    assert next(x for x in report(s=s,d=d).findings if x.ui_field=='analyzed_posts').status == 'structurally_compatible_unapproved'


def test_integer_is_compatible_with_number_declared():
    d = schema_data()
    next(f for f in d['resources'][0]['fields'] if f['name']=='analyzed_total')['data_type']='number'
    assert next(x for x in report(d=d).findings if x.ui_field=='analyzed_posts').status=='structurally_compatible_unapproved'


def test_bool_is_not_an_integer_for_compatibility():
    s = spec_data()
    x = next(f for f in s['candidate_features'][0]['changed_fields'] if f['field']=='analyzed_posts')
    x['before'] = False
    x['after'] = True
    assert next(f for f in report(s=s).findings if f.ui_field=='analyzed_posts').status == 'type_conflict'


def test_mixed_type_is_unknown_without_implicit_coercion():
    s = spec_data()
    x = next(f for f in s['candidate_features'][0]['changed_fields'] if f['field']=='analyzed_posts')
    x['before'] = '153'
    assert next(f for f in report(s=s).findings if f.ui_field=='analyzed_posts').status == 'unknown_ui_type'


def test_only_unknown_observations_yields_empty_findings():
    s = spec_data()
    s['candidate_features'] = []
    d = schema_data()
    d['bindings'] = []  # Stale mappings must be removed rather than silently accepted.
    r = report(s=s, d=d)
    assert r.findings == []
    assert r.unresolved_observation_ids == ['filter_execution_unknown','ratio_formula_unknown']
    assert r.mapping_approved is False


def test_all_unbound_is_reported_not_inferred():
    d = schema_data()
    d['bindings'] = []
    r = report(d=d)
    assert len(r.findings) == 10
    assert all(f.status == 'unmapped' for f in r.findings)


def test_metadata_rejects_unrecognized_properties():
    d = schema_data()
    d['secret_connection_string'] = 'not allowed'
    with pytest.raises(ValidationError):
        report(d=d)


def test_api_response_not_assumed_to_be_accessible_or_live():
    r = report()
    assert r.schema_verified_against_live_system is False
    assert r.mapping_approved is False
    assert all(f.status != 'approved' for f in r.findings)


def test_cli_success_stdout_and_failure_stderr(tmp_path, capsys):
    assert main([str(SPEC),str(SCHEMA)]) == 0
    ok = capsys.readouterr()
    assert json.loads(ok.out)['counts']['unmapped'] == 4
    assert ok.err == ''
    invalid = tmp_path / 'invalid.json'
    invalid.write_text('{"resources":[]}',encoding='utf-8')
    assert main([str(SPEC),str(invalid)]) == 1
    failure = capsys.readouterr()
    assert failure.out == '' and 'FAIL:' in failure.err
    assert list(tmp_path.iterdir()) == [invalid]


def test_generator_has_no_io_backends_or_mutation_calls():
    code = (ROOT/'astra_contracts/data_mapping.py').read_text(encoding='utf-8')
    for forbidden in ('import sqlite3','import requests','import subprocess','import socket',
                      'import urllib.request','openai','execute(', 'requests.get(', 'write_text('):
        assert forbidden not in code


def test_generic_job_search_schema_without_domain_specific_rules():
    s = spec_data()
    s['candidate_features'][0]['observation_id'] = 'job_search'
    s['candidate_features'][0]['feature'] = 'search'
    s['candidate_features'][0]['changed_fields'] = [
        {'field':'query','before':'','after':'python'},
        {'field':'results_count','before':20,'after':5},
    ]
    d = {
        'schema_version':'0.1', 'source_kind':'owner_supplied_document',
        'source_label':'Unverified read-only customer-provided schema description',
        'resources':[{'id':'job_results','kind':'api_response','fields':[
            {'name':'term','data_type':'string','nullable':False},
            {'name':'count','data_type':'integer','nullable':False},
        ]}],
        'bindings':[
            {'observation_id':'job_search','ui_field':'query','resource_id':'job_results','resource_field':'term'},
            {'observation_id':'job_search','ui_field':'results_count','resource_id':'job_results','resource_field':'count'},
        ]
    }
    result = report(s=s,d=d)
    assert result.counts['structurally_compatible_unapproved'] == 2
    assert result.schema_verified_against_live_system is False
    assert result.mapping_approved is False


def test_declared_unknown_type_remains_unapproved_type_conflict():
    d = schema_data()
    d['resources'][0]['fields'][0]['data_type'] = 'unknown'
    findings = {x.ui_field: x for x in report(d=d).findings}
    assert findings['selected_brand'].status == 'type_conflict'
    assert findings['selected_brand'].declared_type.value == 'unknown'
