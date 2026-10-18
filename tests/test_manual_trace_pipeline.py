"""Manual source facts are never inferred from successful fictional smoke checks."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.manual_trace_pipeline import (
    ManualPipelineReport, ManualTrace, run_pipeline, verify_manual_trace, main,
)
from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest, fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.synthetic_generator import SyntheticDemo
from astra_contracts.synthetic_acceptance import check_generated_preview

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.fixture
def parts():
    bundle=ObservationBundle.model_validate_json((FIX/'synthetic_manual_filter_observation_20261019.json').read_text())
    schema=OwnedSchemaDeclaration.model_validate_json((FIX/'synthetic_manual_filter_schema_20261019.json').read_text())
    request=GenerationRequest.model_validate_json((FIX/'synthetic_generation_request_20261018.json').read_text())
    demo=SyntheticDemo.model_validate_json((FIX/'synthetic_demo_catalog_20261018.json').read_text())
    return bundle,schema,request,demo


def altered_observation(bundle, **change):
    d=bundle.model_dump(mode='json')
    d['observations'][0].update(change)
    return ObservationBundle.model_validate(d)


def test_manual_trace_match_and_fingerprint(parts):
    bundle,*_=parts
    trace, digest=verify_manual_trace(bundle,FIX)
    assert trace.observation_id=='demo_category_filter'
    assert trace.evidence_id=='manual_test_demo'
    assert trace.before['visible_items']==4
    assert trace.after['visible_items']==2
    assert len(digest)==64
    assert trace.original_site_behavior_verified is False


def test_complete_pipeline_checks_and_file_preservation(parts):
    bundle,schema,request,demo=parts
    before=fingerprint(bundle)
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        out=Path(t)
        result=run_pipeline(bundle,FIX,schema,request,demo,out)
        assert fingerprint(bundle)==before
        assert result.status=='fictional_end_to_end_smoke_passed'
        assert result.synthetically_illustrated_feature=='filter'
        assert result.synthetic_checks_passed >= 12
        assert result.synthetic_generated_file_count==8
        assert result.mapping_discrepancy_count==0
        assert not result.customer_schema_approved
        assert not result.original_site_behavior_verified
        assert not result.actual_code_generation_authorized
        assert not result.production_ready
        assert not result.deployment_authorized
        assert (out/'app/main.py').is_file()
        assert (out/'data/demo.sqlite3').is_file()
        saved=ManualPipelineReport.model_validate_json((out/'data/manual_pipeline_report.json').read_text())
        assert saved==result
        independently=check_generated_preview(out)
        assert len(independently.checks)==result.synthetic_checks_passed
        trace=json.loads((out/'data/astra_preview_trace.json').read_text())
        assert trace['preflight_status']=='blocked_pending_review'
        assert trace['trace'][0]['result']=='synthetic_smoke_only'
        assert trace['trace'][0]['original_behavior_verified'] is False


def test_cli_runs_exact_end_to_end(parts,capsys):
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        args=[str(FIX/'synthetic_manual_filter_observation_20261019.json'),str(FIX),
              str(FIX/'synthetic_manual_filter_schema_20261019.json'),
              str(FIX/'synthetic_generation_request_20261018.json'),
              str(FIX/'synthetic_demo_catalog_20261018.json'),t]
        assert main(args)==0
        result=json.loads(capsys.readouterr().out)
        assert result['status']=='fictional_end_to_end_smoke_passed'
        assert result['customer_database_accessed'] is False
        assert (Path(t)/'data/manual_pipeline_report.json').is_file()


@pytest.mark.parametrize('field,change',[('observation_id','wrong_id'),('evidence_id','wrong_id'),
                                      ('action','Other invented action')])
def test_trace_metadata_disagreement_rejected(parts,tmp_path,field,change):
    bundle,*_=parts
    src=tmp_path/'evidence';src.mkdir()
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d[field]=change
    (src/'synthetic_manual_filter_trace_20261019.json').write_text(json.dumps(d))
    with pytest.raises(ValueError,match='disagree'):
        verify_manual_trace(bundle,tmp_path)


@pytest.mark.parametrize('change',[{'selected_category':'MODIFIED','visible_items':4},
                                   {'selected_category':'ALL','visible_items':3}])
def test_trace_changed_before_rejected(parts,tmp_path,change):
    bundle,*_=parts
    src=tmp_path/'evidence';src.mkdir()
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d['before']=change
    (src/'synthetic_manual_filter_trace_20261019.json').write_text(json.dumps(d))
    with pytest.raises(ValueError,match='disagree'):
        verify_manual_trace(bundle,tmp_path)


def test_trace_changed_after_rejected(parts,tmp_path):
    bundle,*_=parts
    (tmp_path/'evidence').mkdir()
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d['after']['visible_items']=123
    (tmp_path/'evidence/synthetic_manual_filter_trace_20261019.json').write_text(json.dumps(d))
    with pytest.raises(ValueError,match='disagree'):
        verify_manual_trace(bundle,tmp_path)


def test_disagreement_true_vs_one_type_rejected(parts,tmp_path):
    bundle,*_=parts
    (tmp_path/'evidence').mkdir()
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d['before']['visible_items']=True  # Python True == 1; JSON identities differ
    (tmp_path/'evidence/synthetic_manual_filter_trace_20261019.json').write_text(json.dumps(d))
    with pytest.raises(ValueError,match='disagree'):
        verify_manual_trace(bundle,tmp_path)


def test_unknown_claim_not_eligible(parts):
    bundle,*_=parts
    x=altered_observation(bundle,certainty='unknown',evidence_ids=[])
    with pytest.raises(ValueError,match='observed action'):
        verify_manual_trace(x,FIX)


def test_inferred_claim_not_eligible(parts):
    bundle,*_=parts
    x=altered_observation(bundle,certainty='inferred',evidence_ids=[])
    with pytest.raises(ValueError,match='observed action'):
        verify_manual_trace(x,FIX)


def test_missing_action_not_eligible(parts):
    bundle,*_=parts
    x=altered_observation(bundle,action=None)
    with pytest.raises(ValueError,match='declare an action'):
        verify_manual_trace(x,FIX)


def test_missing_evidence_file_rejected(parts,tmp_path):
    bundle,*_=parts
    with pytest.raises(FileNotFoundError):
        verify_manual_trace(bundle,tmp_path)


def test_symlinked_evidence_rejected(parts,tmp_path):
    bundle,*_=parts
    (tmp_path/'evidence').mkdir()
    (tmp_path/'evidence/synthetic_manual_filter_trace_20261019.json').symlink_to(
        FIX/'evidence/synthetic_manual_filter_trace_20261019.json')
    with pytest.raises(ValueError,match='symbolic'):
        verify_manual_trace(bundle,tmp_path)


def test_malformed_trace_rejected(parts,tmp_path):
    bundle,*_=parts
    (tmp_path/'evidence').mkdir()
    (tmp_path/'evidence/synthetic_manual_filter_trace_20261019.json').write_text('{bad-json')
    with pytest.raises(ValueError):
        verify_manual_trace(bundle,tmp_path)


def test_trace_cannot_claim_user_approval(parts,tmp_path):
    bundle,*_=parts
    (tmp_path/'evidence').mkdir()
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d['approval_granted']=True
    (tmp_path/'evidence/synthetic_manual_filter_trace_20261019.json').write_text(json.dumps(d))
    with pytest.raises(ValidationError):
        verify_manual_trace(bundle,tmp_path)


def test_trace_without_state_change_rejected():
    d=json.loads((FIX/'evidence/synthetic_manual_filter_trace_20261019.json').read_text())
    d['after']=copy.deepcopy(d['before'])
    with pytest.raises(ValidationError,match='changed shared'):
        ManualTrace.model_validate(d)


def test_owner_schema_rejected_before_generation(parts):
    bundle,schema,req,demo=parts
    data=schema.model_dump(mode='json');data['source_kind']='owner_supplied_document'
    schema=OwnedSchemaDeclaration.model_validate(data)
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        with pytest.raises(ValueError,match='real/owner'):
            run_pipeline(bundle,FIX,schema,req,demo,Path(t))
        assert list(Path(t).iterdir())==[]


def test_non_fastapi_stack_rejected_before_generation(parts):
    bundle,schema,req,demo=parts
    x=req.model_dump(mode='json');x['stack']='nextjs_prisma'
    request=GenerationRequest.model_validate(x)
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        with pytest.raises(ValueError,match='FastAPI'):
            run_pipeline(bundle,FIX,schema,request,demo,Path(t))
        assert list(Path(t).iterdir())==[]


def test_nonempty_destination_rejected_preserves_files(parts):
    bundle,schema,req,demo=parts
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        marker=Path(t)/'IMPORTANT.txt';marker.write_text('KEEP')
        with pytest.raises(ValueError,match='EMPTY'):
            run_pipeline(bundle,FIX,schema,req,demo,Path(t))
        assert marker.read_text()=='KEEP'


def test_output_outside_temp_rejected(parts,tmp_path):
    bundle,schema,req,demo=parts
    with pytest.raises(ValueError,match='temporary|temp|empty'):
        run_pipeline(bundle,FIX,schema,req,demo,tmp_path)


def test_old_mapping_for_another_case_cannot_pass(parts):
    bundle,schema,req,demo=parts
    other=OwnedSchemaDeclaration.model_validate_json((FIX/'synthetic_owned_schema_mapping_20261018.json').read_text())
    with tempfile.TemporaryDirectory(prefix='astra-synth-manual-') as t:
        with pytest.raises(ValueError,match='nonexistent candidate fields'):
            run_pipeline(bundle,FIX,other,req,demo,Path(t))
        assert list(Path(t).iterdir())==[]


def test_report_flags_are_literals():
    valid={
        'observation_sha256':'a'*64,'action_trace_sha256':'b'*64,
        'functional_spec_sha256':'c'*64,'mapping_report_sha256':'d'*64,
        'blocked_contract_sha256':'e'*64,'synthetic_fixture_sha256':'f'*64,
        'original_observation_id':'demo_category_filter',
        'synthetically_illustrated_feature':'filter','synthetic_checks_passed':12,
        'synthetic_generated_file_count':8,'mapping_discrepancy_count':0,
    }
    for name in ('original_site_behavior_verified','reviewer_identity_verified',
                 'customer_database_accessed','customer_schema_approved',
                 'actual_code_generation_authorized','production_ready',
                 'deployment_authorized','original_calculation_verified'):
        with pytest.raises(ValidationError):
            ManualPipelineReport.model_validate({**valid,name:True})
