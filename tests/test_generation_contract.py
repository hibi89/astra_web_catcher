"""Step 4-C fail-closed planning-only contract and cross-document integrity."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import GenerationContract, GenerationRequest, main, preflight_contract

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'fixtures'
FILES = {
    'spec': 'jp_nail_functional_spec_draft_20261018.json',
    'schema': 'synthetic_owned_schema_mapping_20261018.json',
    'report': 'synthetic_mapping_report_20261018.json',
    'request': 'synthetic_generation_request_20261018.json',
    'contract': 'synthetic_generation_contract_20261018.json',
}


def load(name):
    return json.loads((FIX / FILES[name]).read_text(encoding='utf-8'))


def make(spec=None, schema=None, report=None, request=None):
    return preflight_contract(
        FunctionalSpecDraft.model_validate(load('spec') if spec is None else spec),
        OwnedSchemaDeclaration.model_validate(load('schema') if schema is None else schema),
        MappingReport.model_validate(load('report') if report is None else report),
        GenerationRequest.model_validate(load('request') if request is None else request),
    )


def test_sample_is_always_blocked_and_contains_no_generated_code():
    result = make()
    assert result.mode == 'contract_only'
    assert result.status == 'blocked_pending_review'
    assert result.code_generated is False and result.files_written is False
    assert result.deployment_permitted is False
    assert result.data_mutation_permitted is False
    assert result.approval_verified is False


def test_status_reasons_for_current_real_archived_observation_plus_synthetic_mapping():
    result = make()
    assert result.observed_candidate_ids == ['brand_all_vs_ohora']
    assert result.block_reasons == sorted({
        'archived_evidence_requires_reverification', 'functional_spec_unapproved',
        'independent_generation_not_authorized', 'mapping_discrepancies',
        'mapping_unapproved', 'schema_is_synthetic',
        'schema_not_verified_live', 'unresolved_observations',
    })
    assert 'confirm_metric_formulas' in result.existing_approval_gates
    assert len(result.required_future_reviews) == 4


def test_only_isolated_path_manifest_and_no_real_output_written(tmp_path):
    planned = make().planned_file_paths
    assert planned == [
        'sandbox/astra-preview/app/main.py', 'sandbox/astra-preview/app/db.py',
        'sandbox/astra-preview/tests/test_app.py', 'sandbox/astra-preview/README.md',
    ]
    assert not (ROOT / 'sandbox').exists()


def test_golden_roundtrip_fingerprints_and_determinism():
    result = make().model_dump(mode='json')
    assert result == load('contract')
    assert make().model_dump(mode='json') == result
    for key in ('spec_sha256', 'schema_sha256', 'report_sha256', 'request_sha256'):
        assert len(result[key]) == 64
    assert result['spec_sha256'] == load('report')['spec_source_sha256']
    assert result['schema_sha256'] == load('report')['declaration_sha256']


@pytest.mark.parametrize('path', [
    '../steal', 'sandbox/../evil', '/tmp/code', 'C:/Users/admin',
    'sandbox\\evil', '~/.ssh', '.hidden', 'safe/.cache',
    'safe//code', 'safe/./code', 'CON', 'safe/NUL.txt',
    'foo.', 'safe/$HOME', 'http://example.com', 'bad name',
    '', 'safe/\x00bad',
])
def test_dangerous_destination_rejected(path):
    obj = load('request')
    obj['destination'] = path
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(obj)


def test_other_supported_stack_is_only_file_manifest():
    req = load('request')
    req['stack'] = 'nextjs_prisma'
    plan = make(request=req)
    assert plan.planned_file_paths == [
        'sandbox/astra-preview/app/page.tsx', 'sandbox/astra-preview/lib/data.ts',
        'sandbox/astra-preview/tests/app.spec.ts', 'sandbox/astra-preview/README.md',
    ]
    assert plan.code_generated is False


@pytest.mark.parametrize('key,value', [
    ('stack', 'shell'), ('mode', 'generate'), ('scope', 'existing_project'),
    ('version', '0.2'), ('destination', '/mnt/data'),
])
def test_unapproved_request_modes_rejected(key, value):
    req = load('request')
    req[key] = value
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(req)


def test_extra_request_key_rejected():
    req = load('request')
    req['overwrite'] = True
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(req)


def test_modified_report_rejected_even_if_it_forged_all_compatible():
    bad = load('report')
    for x in bad['findings']:
        x['status'] = 'structurally_compatible_unapproved'
    with pytest.raises(ValueError, match='does not match'):
        make(report=bad)


def test_modified_report_counts_rejected_even_with_same_fingerprint():
    bad = load('report')
    bad['counts']['unmapped'] = 0
    with pytest.raises(ValueError, match='does not match'):
        make(report=bad)


def test_cross_document_swapped_schema_rejected():
    bad = load('schema')
    bad['source_label'] = 'Modified version'
    with pytest.raises(ValueError, match='does not match'):
        make(schema=bad)


def test_cross_document_swapped_spec_rejected():
    bad = load('spec')
    bad['candidate_features'][0]['title'] = 'Different feature'
    with pytest.raises(ValueError, match='does not match'):
        make(spec=bad)


def test_forged_approval_not_accepted():
    spec = load('spec')
    spec['implementation_ready'] = True
    with pytest.raises(ValidationError):
        make(spec=spec)
    report = load('report')
    report['mapping_approved'] = True
    with pytest.raises(ValidationError):
        make(report=report)


def test_no_candidates_still_blocked_with_recomputed_report():
    spec = load('spec')
    spec['candidate_features'] = []
    schema = load('schema')
    schema['bindings'] = []
    fresh = compare_mappings(FunctionalSpecDraft.model_validate(spec), OwnedSchemaDeclaration.model_validate(schema))
    result = make(spec=spec, schema=schema, report=fresh.model_dump(mode='json'))
    assert result.observed_candidate_ids == []
    assert 'no_observed_feature_candidates' in result.block_reasons
    assert result.code_generated is False


def test_structurally_clean_still_cannot_generate():
    spec = load('spec')
    schema = load('schema')
    for ob in schema['bindings']:
        if ob['resource_id'] == 'missing_resource':
            ob['resource_id'] = 'dashboard_summary'
        if ob['resource_field'] == 'no_such_field':
            ob['resource_field'] = 'sheet_count'
    for field in schema['resources'][0]['fields']:
        if field['name'] == 'avg_reactions':
            field['data_type'] = 'integer'
    # Complete explicit coverage for all other changed fields; source remains synthetic.
    resources = schema['resources'][0]['fields']
    binding_names = {b['ui_field'] for b in schema['bindings']}
    for field in spec['candidate_features'][0]['changed_fields']:
        if field['field'] not in binding_names:
            resources.append({'name': field['field'], 'data_type': 'integer'})
            schema['bindings'].append({'observation_id':'brand_all_vs_ohora', 'ui_field':field['field'],
                                       'resource_id':'dashboard_summary', 'resource_field':field['field']})
    fresh = compare_mappings(FunctionalSpecDraft.model_validate(spec), OwnedSchemaDeclaration.model_validate(schema))
    assert all(x.status == 'structurally_compatible_unapproved' for x in fresh.findings)
    plan = make(spec=spec, schema=schema, report=fresh.model_dump(mode='json'))
    assert 'mapping_discrepancies' not in plan.block_reasons
    assert 'independent_generation_not_authorized' in plan.block_reasons
    assert plan.approval_verified is False


def test_generated_contract_flags_are_literal_false():
    base = load('contract')
    for key in ('code_generated','files_written','deployment_permitted','data_mutation_permitted','approval_verified'):
        test = copy.deepcopy(base)
        test[key] = True
        with pytest.raises(ValidationError):
            GenerationContract.model_validate(test)


def test_cli_json_stdout_only_and_read_only(tmp_path, capsys):
    paths = [str(FIX / FILES[key]) for key in ('spec','schema','report','request')]
    before = {p: Path(p).stat().st_mtime_ns for p in paths}
    assert main(paths) == 0
    printed = capsys.readouterr()
    assert json.loads(printed.out) == load('contract')
    assert printed.err == ''
    assert before == {p: Path(p).stat().st_mtime_ns for p in paths}
    assert list(tmp_path.iterdir()) == []


def test_cli_fails_closed_on_unreadable_file(tmp_path,capsys):
    p = str(tmp_path / 'not_a_report.json')
    paths = [str(FIX / FILES[key]) for key in ('spec','schema')]+[p,str(FIX / FILES['request'])]
    assert main(paths) == 1
    out = capsys.readouterr()
    assert out.out == '' and out.err.startswith('FAIL:')


def test_source_has_no_runtime_execution_or_file_write_logic():
    source = (ROOT / 'astra_contracts/generation_contract.py').read_text(encoding='utf-8')
    for forbidden in ('subprocess', 'requests', 'sqlite3', 'uvicorn', 'openai',
                      '.write_text(', '.write_bytes(', '.mkdir(', 'os.system', 'eval('):
        assert forbidden not in source
