"""Synthetic feature acceptance tests do not verify or reproduce a reference site."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.feature_acceptance_adapter import (
    FeatureAcceptancePlan, FeatureCase, run_feature_acceptance, main,
)
from astra_contracts.generation_contract import GenerationRequest
from astra_contracts.manual_trace_pipeline import run_pipeline
from astra_contracts.observation import ObservationBundle
from astra_contracts.synthetic_generator import SyntheticDemo

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


def load_model(path, model):
    return model.model_validate_json((FIX/path).read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def preview():
    bundle = load_model('synthetic_manual_filter_observation_20261019.json', ObservationBundle)
    schema = load_model('synthetic_manual_filter_schema_20261019.json', OwnedSchemaDeclaration)
    req = load_model('synthetic_generation_request_20261018.json', GenerationRequest)
    demo = load_model('synthetic_demo_catalog_20261018.json', SyntheticDemo)
    with tempfile.TemporaryDirectory(prefix='astra-synth-adapter-') as folder:
        directory=Path(folder)
        run_pipeline(bundle, FIX, schema, req, demo, directory)
        yield bundle,directory


def plan_dict():
    return json.loads((FIX/'synthetic_feature_acceptance_plan_20261019.json').read_text(encoding='utf-8'))


def run(plan, preview):
    bundle, directory = preview
    return run_feature_acceptance(bundle, FIX, directory, plan)


def test_full_fixture_plan_verified(preview):
    result=run(FeatureAcceptancePlan.model_validate(plan_dict()),preview)
    assert result.status=='synthetic_feature_contract_passed'
    assert result.synthetic_cases_passed==8
    assert result.source_illustrations_passed==1
    assert result.fixture_only_cases_passed==7
    assert not result.original_site_behavior_verified
    assert not result.customer_database_accessed
    assert not result.code_generation_authorized
    assert not result.deployment_authorized


def test_deterministic_report_and_no_source_mutation(preview):
    before=preview[0].model_dump_json()
    plan=FeatureAcceptancePlan.model_validate(plan_dict())
    assert run(plan,preview)==run(plan,preview)
    assert preview[0].model_dump_json()==before
    assert not (preview[1]/'data/feature_acceptance_result.json').exists()


@pytest.mark.parametrize('change',[
    {'source_observation_sha256':'0'*64},
    {'prior_pipeline_report_sha256':'1'*64},
    {'synthetic_fixture_sha256':'2'*64},
])
def test_stale_source_or_fixture_fingerprint_fails(preview,change):
    data=plan_dict();data.update(change)
    with pytest.raises(ValueError,match='different|mismatch'):
        run(FeatureAcceptancePlan.model_validate(data),preview)


@pytest.mark.parametrize('key',[
    'original_site_verified','customer_database_permitted','code_generation_authorized'
])
def test_approval_spoofing_rejected(key):
    d=plan_dict();d[key]=True
    with pytest.raises(ValidationError):FeatureAcceptancePlan.model_validate(d)


def test_not_framed_as_source_for_unrelated_list(preview):
    data=plan_dict();data['cases'][1].update({'relationship':'source_feature_illustration',
                                               'source_observation_id':'demo_category_filter'})
    with pytest.raises(ValueError,match='unrelated'):
        run(FeatureAcceptancePlan.model_validate(data),preview)


def test_wrong_observation_id_fails(preview):
    data=plan_dict();data['cases'][0]['source_observation_id']='not-real'
    with pytest.raises(ValueError,match='unrelated'):
        run(FeatureAcceptancePlan.model_validate(data),preview)


def test_fixture_case_cannot_claim_source():
    d=plan_dict();d['cases'][1]['source_observation_id']='demo_category_filter'
    with pytest.raises(ValidationError,match='independent'):
        FeatureAcceptancePlan.model_validate(d)


def test_no_source_illustrations_rejected():
    d=plan_dict();d['cases']=d['cases'][1:]
    with pytest.raises(ValidationError,match='source-feature'):
        FeatureAcceptancePlan.model_validate(d)


def test_wrong_expected_order_fails_before_api(preview):
    d=plan_dict();d['cases'][0]['expected_ids']=['sample-pink','sample-blue']
    with pytest.raises(ValueError,match='fixture expectation'):
        run(FeatureAcceptancePlan.model_validate(d),preview)


def test_invalid_expected_result_fails(preview):
    d=plan_dict();d['cases'][5]['expected_ids']=['sample-blue']
    with pytest.raises(ValueError,match='fixture expectation'):
        run(FeatureAcceptancePlan.model_validate(d),preview)


def test_explicit_404_must_be_correct(preview):
    d=plan_dict();d['cases'][-1]['expected_status']=200
    d['cases'][-1]['expected_ids']=['absent-item']
    with pytest.raises(ValueError,match='fixture expectation'):
        run(FeatureAcceptancePlan.model_validate(d),preview)


@pytest.mark.parametrize('edits',[
    {'feature':'filter','category':None},
    {'feature':'filter','category':''},
    {'feature':'search','q':''},
    {'feature':'search','q':'젤','category':'색상'},
    {'feature':'detail','item_id':'../data'},
    {'feature':'detail','item_id':'sample-blue','q':'a'},
    {'feature':'list','item_id':'sample-blue'},
    {'feature':'list','limit':0},
    {'feature':'list','limit':101},
    {'feature':'filter','expected_status':404},
])
def test_invalid_scenario_shape_rejected(edits):
    d=plan_dict();d['cases'][0].update(edits)
    with pytest.raises(ValidationError):FeatureAcceptancePlan.model_validate(d)


def test_duplicate_case_ids_rejected():
    d=plan_dict();d['cases'][1]['id']=d['cases'][0]['id']
    with pytest.raises(ValidationError,match='duplicate'):
        FeatureAcceptancePlan.model_validate(d)


def test_unknown_feature_rejected():
    d=plan_dict();d['cases'][1]['feature']='create'
    with pytest.raises(ValidationError):FeatureAcceptancePlan.model_validate(d)


def test_no_unrecognized_fields_allowed():
    d=plan_dict();d['cases'][0]['real_database']=True
    with pytest.raises(ValidationError):FeatureAcceptancePlan.model_validate(d)


def test_demo_seed_mutation_blocks_before_app_execution(preview):
    bundle,root=preview
    seed=root/'data/seed.json'
    original=seed.read_bytes()
    try:
        d=json.loads(original)
        d['items'][0]['score']=999
        seed.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
        with pytest.raises(ValueError,match='synthetic|trace|fixture'):
            run(FeatureAcceptancePlan.model_validate(plan_dict()),preview)
    finally:
        seed.write_bytes(original)


def test_app_template_tampering_rejected(preview):
    file=preview[1]/'app/main.py'
    original=file.read_bytes()
    try:
        file.write_bytes(original+b'\n# changed')
        with pytest.raises(ValueError,match='template'):
            run(FeatureAcceptancePlan.model_validate(plan_dict()),preview)
    finally:
        file.write_bytes(original)


def test_original_action_trace_tampered_fails(preview):
    bundle,root=preview
    changed=bundle.model_copy(update={'scope':'a different manual example'})
    with pytest.raises(ValueError,match='different source'):
        run_feature_acceptance(changed,FIX,root,FeatureAcceptancePlan.model_validate(plan_dict()))


def test_untrusted_output_path_rejected(preview,tmp_path):
    with pytest.raises(ValueError,match='astra-synth'):
        run_feature_acceptance(preview[0], FIX,tmp_path, FeatureAcceptancePlan.model_validate(plan_dict()))


def test_cli_prints_json_only_with_no_files_written(preview,tmp_path,capsys):
    observation=tmp_path/'observation.json'
    observation.write_text(preview[0].model_dump_json(),encoding='utf-8')
    before=set(preview[1].rglob('*'))
    assert main([str(observation),str(FIX),str(preview[1]),
                 str(FIX/'synthetic_feature_acceptance_plan_20261019.json')])==0
    response=json.loads(capsys.readouterr().out)
    assert response['synthetic_cases_passed']==8
    assert response['original_site_behavior_verified'] is False
    assert set(preview[1].rglob('*'))==before


def test_invalid_cli_plan_reports_failure(preview,tmp_path,capsys):
    p=tmp_path/'bad.json';p.write_text('{}')
    assert main([str(FIX/'synthetic_manual_filter_observation_20261019.json'),str(FIX),str(preview[1]),str(p)])==1
    assert 'FAIL:' in capsys.readouterr().err
