"""Static screen evidence never becomes interaction or formula proof."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import CaptureIntakeRequest, register_captures
from astra_contracts.evidence_claim_levels import (
    AssertionLayer, ClaimLevelPacket, GateState, LayerSubmission,
    LayerReviewRecord, build_level_packet, record_layer_notes, main,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.fixture
def scenario():
    bundle = ObservationBundle.model_validate_json(
        (FIX / 'synthetic_capture_observation_20261018.json').read_text(encoding='utf-8'))
    request = CaptureIntakeRequest.model_validate_json(
        (FIX / 'synthetic_capture_intake_request_20261018.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as temp:
        folder = Path(temp)
        register_captures(bundle, FIX, request, folder)
        yield bundle, folder


def note(packet, observation='example_filter', layer='visible_state',
         outcome='needs_more_evidence', evidence=None):
    return LayerSubmission.model_validate({
        'version': '0.1', 'packet_sha256':fingerprint(packet),
        'reviewer_claimed_label':'Fictional reviewer (NOT authenticated)',
        'notes':[{'observation_id':observation,'layer':layer,'outcome':outcome,
                  'evidence_ids_checked':[] if evidence is None else evidence,
                  'rationale':'Unverified demonstration; original site never contacted.'}],
    })


def get(packet, observation, layer):
    return next(x for x in packet.items if x.observation_id == observation and x.layer.value == layer)


def test_visible_text_is_only_review_candidate(scenario):
    bundle,folder=scenario
    result=build_level_packet(bundle,folder)
    assert result.status=='human_review_queue_only'
    assert len(result.items)==6
    visual=get(result,'example_filter','visible_state')
    assert visual.evidence_ids==['sample_dom_capture']
    assert visual.status==GateState.VISIBLE_REVIEW_CANDIDATE
    assert not visual.visually_verified and not visual.interaction_verified and not visual.formula_verified
    assert not result.original_behavior_verified and not result.formula_verified


def test_static_dom_does_not_show_interaction(scenario):
    p=build_level_packet(*scenario)
    row=get(p,'example_filter','interaction_transition')
    assert row.status==GateState.MISSING_RECORDED_SEQUENCE
    assert row.evidence_ids==[]


def test_static_dom_does_not_prove_formula(scenario):
    p=build_level_packet(*scenario)
    assert get(p,'example_filter','calculation_formula').status==GateState.FORMULA_AUDIT_REQUIRED
    assert get(p,'example_filter','calculation_formula').evidence_ids==[]


def test_unknown_formula_stays_unknown_in_all_layers(scenario):
    p=build_level_packet(*scenario)
    for layer in AssertionLayer:
        row=get(p,'example_formula_unknown',layer.value)
        assert row.original_claim_certainty.value == 'unknown'
        assert not row.visually_verified and not row.formula_verified


def test_repeatability_and_source_immutability(scenario):
    bundle,folder=scenario
    digest=fingerprint(bundle)
    first=build_level_packet(bundle,folder)
    assert first==build_level_packet(bundle,folder)
    assert fingerprint(bundle)==digest
    assert not (folder/'evidence_level_review.json').exists()


def test_visual_note_can_be_recorded_but_never_verified(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    r=record_layer_notes(bundle,folder,note(p,outcome='looks_consistent_but_not_verified',
                                           evidence=['sample_dom_capture']))
    assert r.status=='unverified_human_notes_only'
    assert r.pending_layers==5 and len(r.notes)==1
    assert not r.original_behavior_verified and not r.interaction_verified
    assert not r.formula_verified and not r.database_access_authorized
    assert not r.code_generation_authorized and not r.deployment_authorized


def test_pending_note_allowed_without_capture(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    r=record_layer_notes(bundle,folder,note(p,'example_formula_unknown','calculation_formula'))
    assert r.pending_layers==5
    assert r.notes[0].outcome=='needs_more_evidence'


def test_visual_consistency_requires_capture(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    with pytest.raises(ValueError, match='requires a linked'):
        record_layer_notes(bundle,folder,note(p,outcome='looks_consistent_but_not_verified'))


def test_visual_consistency_cannot_use_unlinked_capture(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    with pytest.raises(ValueError, match='ineligible'):
        record_layer_notes(bundle,folder,note(p,'example_formula_unknown',outcome='looks_consistent_but_not_verified',evidence=['sample_dom_capture']))


def test_interaction_consistency_cannot_use_static_capture(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    with pytest.raises(ValueError, match='ineligible'):
        record_layer_notes(bundle,folder,note(p,layer='interaction_transition',outcome='looks_consistent_but_not_verified',evidence=['sample_dom_capture']))


def test_formula_never_consistent(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    with pytest.raises(ValueError, match='requires a linked'):
        record_layer_notes(bundle,folder,note(p,layer='calculation_formula',outcome='looks_consistent_but_not_verified'))


def test_inconsistent_and_stale_packet_rejected(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    bad=note(p).model_dump(mode='json')
    bad['packet_sha256']='a'*64
    with pytest.raises(ValueError, match='stale'):
        record_layer_notes(bundle,folder,LayerSubmission.model_validate(bad))


def test_packet_forbidden_authorization(scenario):
    obj=build_level_packet(*scenario).model_dump(mode='json')
    obj['deployment_authorized']=True
    with pytest.raises(ValidationError):
        ClaimLevelPacket.model_validate(obj)


def test_record_forbidden_verified_flags(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    record=record_layer_notes(bundle,folder,note(p)).model_dump(mode='json')
    for flag in ['original_behavior_verified','interaction_verified','formula_verified',
                 'code_generation_authorized','database_access_authorized','deployment_authorized']:
        altered=copy.deepcopy(record)
        altered[flag]=True
        with pytest.raises(ValidationError):
            LayerReviewRecord.model_validate(altered)


def test_duplicate_note_rejected(scenario):
    p=build_level_packet(*scenario)
    raw=note(p).model_dump(mode='json')
    raw['notes'].append(copy.deepcopy(raw['notes'][0]))
    with pytest.raises(ValidationError, match='duplicate'):
        LayerSubmission.model_validate(raw)


def test_duplicate_evidence_rejected(scenario):
    p=build_level_packet(*scenario)
    raw=note(p).model_dump(mode='json')
    raw['notes'][0]['evidence_ids_checked']=['sample_dom_capture']*2
    with pytest.raises(ValidationError, match='duplicate'):
        LayerSubmission.model_validate(raw)


def test_bad_layer_and_extra_consent_rejected(scenario):
    p=build_level_packet(*scenario)
    raw=note(p).model_dump(mode='json')
    raw['notes'][0]['layer']='unrestricted_auth'
    with pytest.raises(ValidationError):
        LayerSubmission.model_validate(raw)
    raw=note(p).model_dump(mode='json')
    raw['user_approved']=True
    with pytest.raises(ValidationError):
        LayerSubmission.model_validate(raw)


def test_unknown_observation_id_rejected(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    with pytest.raises(ValueError,match='nonexistent'):
        record_layer_notes(bundle,folder,note(p,'invented_observation'))


def test_capture_tamper_prevents_packet_and_record(scenario):
    bundle,folder=scenario
    p=build_level_packet(bundle,folder)
    f=folder/'captures/sample_dom_capture.txt'
    f.write_text('changed file',encoding='utf-8')
    with pytest.raises(ValueError,match='byte-integrity'):
        build_level_packet(bundle,folder)
    with pytest.raises(ValueError,match='byte-integrity'):
        record_layer_notes(bundle,folder,note(p))


def test_changed_bundle_rejected(scenario):
    bundle,folder=scenario
    changed=bundle.model_copy(update={'scope':'changed'})
    with pytest.raises(ValueError,match='different observation'):
        build_level_packet(changed,folder)


def test_sequence_with_manual_test_and_changed_value_creates_candidate(scenario,tmp_path):
    bundle,_=scenario
    source=tmp_path/'source'
    (source/'evidence').mkdir(parents=True)
    (source/'evidence/action.txt').write_text('SYNTHETIC click category: state a -> b',encoding='utf-8')
    observation=bundle.observations[0].model_copy(update={
        'action':'click category', 'before':{'category':'ALL'},'after':{'category':'B'},
    })
    changed=bundle.model_copy(update={'observations':[observation,bundle.observations[1]]})
    raw={'version':'0.1','source_kind':'manually_supplied_local_files',
         'observation_sha256':fingerprint(changed),
         'captures':[{'evidence':{'id':'manual_trace','kind':'manual_test',
              'source_ref':'evidence/action.txt','captured_at':'2026-10-18T12:00:00+09:00',
              'notes':'fictional'},'observation_ids':['example_filter']}]}
    req=CaptureIntakeRequest.model_validate(raw)
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as path:
        folder=Path(path)
        register_captures(changed,source,req,folder)
        p=build_level_packet(changed,folder)
        row=get(p,'example_filter','interaction_transition')
        assert row.status==GateState.TRANSITION_REVIEW_CANDIDATE
        assert row.evidence_ids==['manual_trace']
        assert get(p,'example_filter','visible_state').status==GateState.MISSING_DIRECT_VISUAL_EVIDENCE
        assert get(p,'example_filter','calculation_formula').status==GateState.FORMULA_AUDIT_REQUIRED
        record=record_layer_notes(changed,folder,note(p,layer='interaction_transition',
             outcome='looks_consistent_but_not_verified',evidence=['manual_trace']))
        assert not record.interaction_verified and not record.original_behavior_verified


def test_sequence_missing_action_not_enough(scenario,tmp_path):
    bundle,_=scenario
    source=tmp_path/'source';(source/'evidence').mkdir(parents=True)
    (source/'evidence/action.txt').write_text('SYNTHETIC manual action only',encoding='utf-8')
    observation=bundle.observations[0].model_copy(update={'before':{'x':1},'after':{'x':2},'action':None})
    changed=bundle.model_copy(update={'observations':[observation,bundle.observations[1]]})
    req=CaptureIntakeRequest.model_validate({'version':'0.1','source_kind':'manually_supplied_local_files',
       'observation_sha256':fingerprint(changed),'captures':[{'evidence':{'id':'manual_trace',
       'kind':'manual_test','source_ref':'evidence/action.txt','captured_at':'2026-10-18T12:00:00+09:00',
       'notes':'synthetic'},'observation_ids':['example_filter']}]})
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as path:
        register_captures(changed,source,req,Path(path))
        p=build_level_packet(changed,Path(path))
        assert get(p,'example_filter','interaction_transition').status==GateState.MISSING_RECORDED_SEQUENCE


def test_cli_packet_record_and_no_folder_changes(scenario,tmp_path,capsys):
    bundle,folder=scenario
    f=tmp_path/'observation.json'; f.write_text(bundle.model_dump_json(),encoding='utf-8')
    before=sorted(x.name for x in folder.rglob('*'))
    assert main(['packet',str(f),str(folder)])==0
    p=json.loads(capsys.readouterr().out)
    assert len(p['items'])==6
    packet=ClaimLevelPacket.model_validate(p)
    input_file=tmp_path/'response.json'
    input_file.write_text(note(packet).model_dump_json(),encoding='utf-8')
    assert main(['record',str(f),str(folder),str(input_file)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='unverified_human_notes_only'
    assert sorted(x.name for x in folder.rglob('*'))==before


def test_unknown_cannot_be_consistent_even_with_visual_file(scenario,tmp_path):
    bundle,_=scenario
    src=tmp_path/'source';(src/'evidence').mkdir(parents=True)
    (src/'evidence/view.txt').write_text('Fictional static text only',encoding='utf-8')
    req=CaptureIntakeRequest.model_validate({'version':'0.1','source_kind':'manually_supplied_local_files',
      'observation_sha256':fingerprint(bundle),'captures':[{'evidence':{'id':'unknown_dom',
      'kind':'dom_text','source_ref':'evidence/view.txt', 'captured_at':'2026-10-18T12:00:00+09:00',
      'notes':'fictional'},'observation_ids':['example_formula_unknown']}]})
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as path:
        folder=Path(path);register_captures(bundle,src,req,folder)
        p=build_level_packet(bundle,folder)
        with pytest.raises(ValueError,match='unknown'):
            record_layer_notes(bundle,folder,note(p,'example_formula_unknown',
             'visible_state','looks_consistent_but_not_verified',['unknown_dom']))
