"""Before/after ledger: byte integrity is not screenshot authenticity or authority."""
from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import CaptureIntakeRequest, register_captures
from astra_contracts.capture_transition_ledger import (
    TransitionPlan, build_transition_ledger, main,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle

T0 = datetime(2026, 10, 19, 3, 5, tzinfo=timezone(timedelta(hours=9)))


def make_observation(*, certainty='observed', action='select category colors',
                     before='all', after='colors'):
    return ObservationBundle.model_validate({
        'schema_version': '1.0', 'site_url': 'https://example.org/fictional-no-visit',
        'scope': 'fictional capture pair test (no real site visited)',
        'recorded_at': T0.isoformat(),
        'evidence': [{'id':'operator_note','kind':'manual_test','source_ref':'notes/fake.txt',
                      'captured_at':T0.isoformat(),'notes':'operator-reported only'}] if certainty == 'observed' else [],
        'observations': [{'id':'category_observation', 'feature':'filter','title':'fictional selection',
                          'claim':'Operator reports a synthetic state change', 'certainty':certainty,
                          'evidence_ids':['operator_note'] if certainty=='observed' else [],
                          'action':action, 'before':{'category':before}, 'after':{'category':after}}],
    })


def make_request(bundle, before_kind='dom_text', after_kind='dom_text',
                 before_time=T0, after_time=T0+timedelta(seconds=4)):
    return CaptureIntakeRequest.model_validate({
        'version':'0.1','source_kind':'manually_supplied_local_files',
        'observation_sha256':fingerprint(bundle),
        'captures':[
            {'evidence':{'id':'before_capture','kind':before_kind,
                         'source_ref':'before.txt' if before_kind=='dom_text' else 'before.png',
                         'captured_at':before_time.isoformat()},
             'observation_ids':['category_observation']},
            {'evidence':{'id':'after_capture','kind':after_kind,
                         'source_ref':'after.txt' if after_kind=='dom_text' else 'after.png',
                         'captured_at':after_time.isoformat()},
             'observation_ids':['category_observation']},
        ]})


def make_plan(bundle, manifest, **changes):
    return TransitionPlan.model_validate({
        'version':'0.1', 'source_kind':'untrusted_local_operator_capture_pair',
        'original_bundle_sha256':fingerprint(bundle),
        'intake_manifest_sha256':fingerprint(manifest),
        'proposals':[{'id':'pair_one','observation_id':'category_observation',
                      'before_capture_id':'before_capture','after_capture_id':'after_capture',
                      'changed_field':'category','operator_action':'select category colors', **changes}],
    })


@pytest.fixture
def fixture_pair():
    bundle = make_observation()
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('SIMULATED DOM state: all',encoding='utf-8')
        Path(src,'after.txt').write_text('SIMULATED DOM state: colors',encoding='utf-8')
        manifest = register_captures(bundle, Path(src), make_request(bundle), Path(out))
        yield bundle,Path(out),manifest


def test_structural_pair_is_unverified_and_disabled(fixture_pair):
    bundle,out,manifest=fixture_pair
    ledger=build_transition_ledger(bundle,out,make_plan(bundle,manifest))
    assert ledger.findings[0].status=='paired_bytes_present_unverified'
    assert ledger.findings[0].before_value=='all'
    assert ledger.findings[0].after_value=='colors'
    assert ledger.byte_integrity_checked
    assert not ledger.original_site_behavior_verified
    assert not ledger.screenshot_meaning_checked
    assert not ledger.ui_controls_enabled
    assert not ledger.code_generation_authorized
    assert not ledger.owner_database_access_authorized
    assert not ledger.deployment_authorized
    assert ledger.human_review_required
    assert build_transition_ledger(bundle,out,make_plan(bundle,manifest))==ledger


def test_original_sources_unchanged(fixture_pair):
    bundle,out,manifest=fixture_pair
    before=fingerprint(bundle)
    file_before=(out/'captures/before_capture.txt').read_bytes()
    build_transition_ledger(bundle,out,make_plan(bundle,manifest))
    assert fingerprint(bundle)==before
    assert (out/'captures/before_capture.txt').read_bytes()==file_before
    assert sorted(p.name for p in out.iterdir())==['capture_intake.json','captures']

@pytest.mark.parametrize('modification', ['before','after','missing','symlink'])
def test_modified_or_missing_capture_fails_closed(fixture_pair,modification):
    bundle,out,manifest=fixture_pair
    p=out/'captures/before_capture.txt'
    if modification=='before': p.write_text('tampered',encoding='utf-8')
    if modification=='after': (out/'captures/after_capture.txt').write_text('tampered',encoding='utf-8')
    if modification=='missing': p.unlink()
    if modification=='symlink':
        p.unlink()
        p.symlink_to(out/'captures/after_capture.txt')
    with pytest.raises(ValueError,match='byte-integrity'):
        build_transition_ledger(bundle,out,make_plan(bundle,manifest))

@pytest.mark.parametrize('field,bad_value',[
    ('original_bundle_sha256','0'*64),('intake_manifest_sha256','f'*64)
])
def test_stale_hash_rejected(fixture_pair,field,bad_value):
    bundle,out,manifest=fixture_pair
    raw=make_plan(bundle,manifest).model_dump(mode='json')
    raw[field]=bad_value
    with pytest.raises(ValueError,match='stale'):
        build_transition_ledger(bundle,out,TransitionPlan.model_validate(raw))

@pytest.mark.parametrize('changes,pattern', [
    ({'observation_id':'unknown_observation'},'unknown observation'),
    ({'before_capture_id':'unknown_capture'},'unknown before/after'),
    ({'after_capture_id':'before_capture'},'distinct'),
])
def test_broken_capture_reference_fails(fixture_pair,changes,pattern):
    bundle,out,manifest=fixture_pair
    with pytest.raises((ValueError,ValidationError),match=pattern):
        p=make_plan(bundle,manifest,**changes)
        build_transition_ledger(bundle,out,p)

@pytest.mark.parametrize('extra', [
    {'original_site_behavior_verified': True},
    {'deployment_authorized': True},
    {'reviewer_verified': True},
    {'source_kind':'authorized_real_capture'},
])
def test_permission_forgery_rejected(fixture_pair,extra):
    bundle,_,manifest=fixture_pair
    data=make_plan(bundle,manifest).model_dump(mode='json')
    data.update(extra)
    with pytest.raises(ValidationError):
        TransitionPlan.model_validate(data)


def test_inferred_claim_not_upgraded():
    bundle=make_observation(certainty='inferred')
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('fake before',encoding='utf-8')
        Path(src,'after.txt').write_text('fake after',encoding='utf-8')
        manifest=register_captures(bundle,Path(src),make_request(bundle),Path(out))
        result=build_transition_ledger(bundle,Path(out),make_plan(bundle,manifest))
        assert result.findings[0].status=='source_claim_unconfirmed'
        assert not result.ui_controls_enabled

@pytest.mark.parametrize('before,after,action,expected',[
    ('all','all','select category colors','unchanged_claimed_field'),
    ('all','colors',None,'missing_or_mismatched_action'),
    ('all',20,'select category colors','missing_comparable_before_after'),
])
def test_unusable_source_state(before,after,action,expected):
    bundle=make_observation(before=before,after=after,action=action)
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('before',encoding='utf-8')
        Path(src,'after.txt').write_text('after',encoding='utf-8')
        manifest=register_captures(bundle,Path(src),make_request(bundle),Path(out))
        finding=build_transition_ledger(bundle,Path(out),make_plan(bundle,manifest)).findings[0]
        assert finding.status==expected
        assert not finding.allowed_to_enable_ui

@pytest.mark.parametrize('before_time,after_time,expected', [
    (T0,T0,'capture_order_invalid'),
    (T0+timedelta(minutes=1),T0,'capture_order_invalid'),
])
def test_timestamp_order(before_time,after_time,expected):
    bundle=make_observation()
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('before',encoding='utf-8')
        Path(src,'after.txt').write_text('after',encoding='utf-8')
        manifest=register_captures(bundle,Path(src),make_request(bundle,before_time=before_time,after_time=after_time),Path(out))
        assert build_transition_ledger(bundle,Path(out),make_plan(bundle,manifest)).findings[0].status==expected


def test_incomparable_capture_kinds():
    bundle=make_observation()
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('before',encoding='utf-8')
        Path(src,'after.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'fictional and intentionally not a real screenshot')
        manifest=register_captures(bundle,Path(src),make_request(bundle,after_kind='screenshot'),Path(out))
        assert build_transition_ledger(bundle,Path(out),make_plan(bundle,manifest)).findings[0].status=='incomparable_capture_kinds'


def test_duplicate_plan_proposals_rejected(fixture_pair):
    bundle,_,manifest=fixture_pair
    raw=make_plan(bundle,manifest).model_dump(mode='json')
    raw['proposals'].append(copy.deepcopy(raw['proposals'][0]))
    with pytest.raises(ValidationError,match='duplicate'):
        TransitionPlan.model_validate(raw)


def test_cli_emits_review_only_json(fixture_pair,tmp_path,capsys):
    bundle,out,manifest=fixture_pair
    b=tmp_path/'bundle.json';p=tmp_path/'plan.json'
    b.write_text(bundle.model_dump_json(),encoding='utf-8')
    p.write_text(make_plan(bundle,manifest).model_dump_json(),encoding='utf-8')
    assert main([str(b),str(out),str(p)])==0
    doc=json.loads(capsys.readouterr().out)
    assert doc['status']=='evidence_pair_triage_only'
    assert doc['ui_controls_enabled'] is False


def test_cli_fails_for_stale_inputs(fixture_pair,tmp_path,capsys):
    bundle,out,manifest=fixture_pair
    b=tmp_path/'bundle.json';p=tmp_path/'plan.json'
    b.write_text(bundle.model_dump_json(),encoding='utf-8')
    raw=make_plan(bundle,manifest).model_dump(mode='json')
    raw['intake_manifest_sha256']='a'*64
    p.write_text(json.dumps(raw),encoding='utf-8')
    assert main([str(b),str(out),str(p)])==1
    assert 'stale' in capsys.readouterr().err


def test_fixed_example_fixture_roundtrip_and_no_authority(tmp_path):
    fix = Path(__file__).resolve().parents[1] / 'fixtures'
    bundle = ObservationBundle.model_validate_json(
        (fix/'synthetic_transition_pair_observation_20261019.json').read_text(encoding='utf-8'))
    request = CaptureIntakeRequest.model_validate_json(
        (fix/'synthetic_transition_pair_intake_request_20261019.json').read_text(encoding='utf-8'))
    plan = TransitionPlan.model_validate_json(
        (fix/'synthetic_transition_pair_plan_20261019.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as dest:
        manifest = register_captures(bundle, fix, request, Path(dest))
        assert fingerprint(manifest) == plan.intake_manifest_sha256
        result = build_transition_ledger(bundle,Path(dest),plan)
        assert result.findings[0].status == 'paired_bytes_present_unverified'
        assert result.findings[0].changed_field == 'category'
        assert result.original_site_behavior_verified is False
        assert result.ui_controls_enabled is False
        assert result.human_review_required is True


def test_unlinked_pair_rejected():
    bundle = make_observation()
    with tempfile.TemporaryDirectory(prefix='astra-transition-source-') as src, \
         tempfile.TemporaryDirectory(prefix='astra-capture-') as out:
        Path(src,'before.txt').write_text('before',encoding='utf-8')
        Path(src,'after.txt').write_text('after',encoding='utf-8')
        request = make_request(bundle).model_dump(mode='json')
        # Entirely valid registered capture IDs, but one is not associated with
        # the requested transition observation.
        request['captures'][1]['observation_ids'] = ['other_observation']
        ob=bundle.model_dump(mode='json')
        ob['observations'].append({'id':'other_observation','feature':'filter','title':'another',
                                   'claim':'another synthetic state','certainty':'unknown',
                                   'evidence_ids':[],'action':None,'before':{},'after':{}})
        bundle=ObservationBundle.model_validate(ob)
        request['observation_sha256']=fingerprint(bundle)
        manifest=register_captures(bundle,Path(src),CaptureIntakeRequest.model_validate(request),Path(out))
        with pytest.raises(ValueError,match='linked to the same observation'):
            build_transition_ledger(bundle,Path(out),make_plan(bundle,manifest))
