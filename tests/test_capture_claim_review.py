"""Capture-linked reviewer opinions are not proof of original behavior/approval."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import CaptureIntakeRequest, register_captures
from astra_contracts.capture_claim_review import (
    ClaimReviewPacket, ClaimReviewRecord, ClaimReviewSubmission,
    build_claim_review_packet, main, record_claim_opinions,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.fixture
def case():
    bundle = ObservationBundle.model_validate_json(
        (FIX / 'synthetic_capture_observation_20261018.json').read_text(encoding='utf-8'))
    request = CaptureIntakeRequest.model_validate_json(
        (FIX / 'synthetic_capture_intake_request_20261018.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as folder:
        path = Path(folder)
        register_captures(bundle, FIX, request, path)
        packet = build_claim_review_packet(bundle, path)
        yield bundle, path, packet


def submission(packet, observation='example_filter', decision='more_evidence_needed',
               captures=None):
    return ClaimReviewSubmission.model_validate({
        'version':'0.1', 'packet_sha256':fingerprint(packet),
        'reviewer_claimed_label':'test operator (NOT VERIFIED)',
        'opinions':[{'observation_id':observation, 'decision':decision,
                     'capture_ids_checked':[] if captures is None else captures,
                     'rationale':'Fictional screenshot or DOM review; do not infer real behavior.'}],
    })


def test_packet_includes_all_source_observations_even_without_captures(case):
    _,_,packet=case
    assert packet.status=='manual_capture_claim_review_pending'
    assert len(packet.items)==2
    assert packet.source_evidence_count==1
    by_id={x.observation_id:x for x in packet.items}
    assert by_id['example_filter'].capture_ids==['sample_dom_capture']
    assert by_id['example_filter'].visible_capture_ids==['sample_dom_capture']
    assert by_id['example_formula_unknown'].capture_ids==[]
    assert by_id['example_formula_unknown'].certainty_at_source.value=='unknown'
    assert packet.byte_integrity_passed and not packet.capture_authenticity_verified
    assert not packet.original_behavior_verified and not packet.authorization_granted


def test_packet_repeatable_and_source_unchanged(case):
    bundle,path,packet=case
    before=fingerprint(bundle)
    assert build_claim_review_packet(bundle,path)==packet
    assert fingerprint(bundle)==before
    assert not (path/'claim_review.json').exists()


def test_allow_pending_without_capture(case):
    _,_,packet=case
    record=record_claim_opinions(packet,submission(packet,observation='example_formula_unknown'))
    assert record.recorded_opinion_count==1
    assert record.pending_review_count==1
    assert record.opinions[0].decision=='more_evidence_needed'
    assert not record.original_behavior_verified
    assert not record.code_generation_authorized


def test_allow_visible_consistency_as_unverified_opinion_only(case):
    _,_,packet=case
    record=record_claim_opinions(packet,submission(packet,decision='appears_consistent_with_visible_capture',
                                                   captures=['sample_dom_capture']))
    assert record.opinions[0].decision=='appears_consistent_with_visible_capture'
    assert record.original_bundle_modified is False
    assert record.capture_authenticity_verified is False
    assert record.mapping_approved is False
    assert record.database_access_authorized is False
    assert record.deployment_authorized is False
    assert record.reviewer_identity_verified is False


def test_allow_visible_contradiction_as_unverified_opinion_only(case):
    _,_,packet=case
    record=record_claim_opinions(packet,submission(packet,decision='appears_inconsistent_with_visible_capture',
                                                   captures=['sample_dom_capture']))
    assert record.recorded_opinion_count==1
    assert record.formula_verified is False


def test_unknown_behavior_cannot_be_consistent_even_with_capture(case):
    _,_,packet=case
    raw=submission(packet,observation='example_formula_unknown',
          decision='appears_consistent_with_visible_capture',captures=['sample_dom_capture'])
    with pytest.raises(ValueError,match='unlinked'):
        record_claim_opinions(packet,raw)
    # Even a forged packet that links one genuine file cannot promote unknown.
    fake=packet.model_copy(deep=True)
    for item in fake.items:
        if item.observation_id=='example_formula_unknown':
            item.capture_ids=['sample_dom_capture']
            item.visible_capture_ids=['sample_dom_capture']
    with pytest.raises(ValueError,match='unknown behavior'):
        record_claim_opinions(fake,submission(fake,observation='example_formula_unknown',
           decision='appears_consistent_with_visible_capture',captures=['sample_dom_capture']))


def test_consistency_requires_actual_checked_capture(case):
    _,_,packet=case
    with pytest.raises(ValueError,match='needs checked'):
        record_claim_opinions(packet,submission(packet,decision='appears_consistent_with_visible_capture'))


def test_wrong_observation_or_capture_rejected(case):
    _,_,packet=case
    with pytest.raises(ValueError,match='unknown observation'):
        record_claim_opinions(packet,submission(packet,observation='fabricated_observation'))
    with pytest.raises(ValueError,match='unlinked'):
        record_claim_opinions(packet,submission(packet,decision='appears_inconsistent_with_visible_capture',
                                               captures=['unknown_capture']))


def test_duplicate_opinions_rejected(case):
    _,_,packet=case
    s=submission(packet).model_dump(mode='json')
    s['opinions'].append(copy.deepcopy(s['opinions'][0]))
    with pytest.raises(ValidationError,match='duplicate'):
        ClaimReviewSubmission.model_validate(s)


def test_duplicate_checked_capture_id_rejected(case):
    _,_,packet=case
    s=submission(packet).model_dump(mode='json')
    s['opinions'][0]['capture_ids_checked']=['sample_dom_capture','sample_dom_capture']
    with pytest.raises(ValidationError,match='duplicate'):
        ClaimReviewSubmission.model_validate(s)


def test_stale_packet_fingerprint_rejected(case):
    _,_,packet=case
    s=submission(packet)
    fake=packet.model_copy(deep=True)
    fake.items[0].claim+=' altered'
    with pytest.raises(ValueError,match='stale'):
        record_claim_opinions(fake,s)


def test_modified_registered_capture_rejected_before_review(case):
    bundle,path,_=case
    (path/'captures/sample_dom_capture.txt').write_text('manipulated and not the same length',encoding='utf-8')
    with pytest.raises(ValueError,match='byte-integrity'):
        build_claim_review_packet(bundle,path)


def test_missing_registered_capture_rejected_before_review(case):
    bundle,path,_=case
    (path/'captures/sample_dom_capture.txt').unlink()
    with pytest.raises(ValueError,match='byte-integrity'):
        build_claim_review_packet(bundle,path)


def test_reject_wrong_bundle(case):
    bundle,path,_=case
    modified=bundle.model_copy(update={'scope':'different source'})
    with pytest.raises(ValueError,match='different observation'):
        build_claim_review_packet(modified,path)


def test_reject_forged_packet_permission_fields(case):
    _,_,packet=case
    for key in ['capture_authenticity_verified','original_behavior_verified','formula_verified',
                'reviewer_identity_verified','authorization_granted']:
        d=packet.model_dump(mode='json')
        d[key]=True
        with pytest.raises(ValidationError):
            ClaimReviewPacket.model_validate(d)


def test_reject_forged_record_permission_fields(case):
    _,_,packet=case
    data=record_claim_opinions(packet,submission(packet)).model_dump(mode='json')
    for key in ['original_bundle_modified','original_behavior_verified','capture_authenticity_verified',
                'formula_verified','reviewer_identity_verified','mapping_approved',
                'code_generation_authorized','database_access_authorized','deployment_authorized']:
        d=copy.deepcopy(data)
        d[key]=True
        with pytest.raises(ValidationError):
            ClaimReviewRecord.model_validate(d)


def test_untrusted_network_capture_cannot_support_visible_consistency(case):
    _,_,packet=case
    fake=packet.model_copy(deep=True)
    fake.items[0].capture_ids.append('sample_network_capture')
    assert 'sample_network_capture' not in fake.items[0].visible_capture_ids
    with pytest.raises(ValueError,match='screenshot or DOM'):
        record_claim_opinions(fake,submission(fake,decision='appears_consistent_with_visible_capture',
                                               captures=['sample_network_capture']))


def test_record_roundtrip_and_still_not_authorized(case):
    _,_,packet=case
    record=record_claim_opinions(packet,submission(packet))
    assert ClaimReviewRecord.model_validate_json(record.model_dump_json())==record
    assert record.status=='unverified_opinion_record_only'


def test_read_only_cli_packet_and_record(case,tmp_path,capsys):
    bundle,folder,packet=case
    original=bundle.model_dump_json()
    bundle_file=tmp_path/'bundle.json';bundle_file.write_text(original,encoding='utf-8')
    assert main(['packet',str(bundle_file),str(folder)])==0
    out=json.loads(capsys.readouterr().out)
    assert ClaimReviewPacket.model_validate(out)==packet
    s=submission(packet)
    sub_file=tmp_path/'submission.json';sub_file.write_text(s.model_dump_json(),encoding='utf-8')
    assert main(['record',str(bundle_file),str(folder),str(sub_file)])==0
    output=json.loads(capsys.readouterr().out)
    assert output['status']=='unverified_opinion_record_only'
    assert output['code_generation_authorized'] is False
    assert bundle_file.read_text(encoding='utf-8')==original
    assert sorted(x.name for x in folder.iterdir())==['capture_intake.json','captures']


def test_cli_corrupted_registered_capture_fails_closed(case,tmp_path,capsys):
    bundle,folder,_=case
    file=tmp_path/'bundle.json';file.write_text(bundle.model_dump_json(),encoding='utf-8')
    (folder/'captures/sample_dom_capture.txt').unlink()
    assert main(['packet',str(file),str(folder)])==1
    out=capsys.readouterr()
    assert out.out=='' and out.err.startswith('FAIL:')


def test_cli_bad_args_fail_and_do_not_write(case,tmp_path,capsys):
    bundle,folder,_=case
    file=tmp_path/'bundle.json';file.write_text(bundle.model_dump_json(),encoding='utf-8')
    assert main(['packet',str(file),str(folder)])==0
    assert 'original_behavior_verified' in capsys.readouterr().out


def test_cannot_review_path_outside_guarded_temp_root(case,tmp_path):
    bundle,_,_=case
    with pytest.raises(ValueError,match='temporary'):
        build_claim_review_packet(bundle,tmp_path)


def test_source_type_not_automatically_changed(case):
    bundle,folder,_=case
    before={o.id:o.certainty for o in bundle.observations}
    build_claim_review_packet(bundle,folder)
    after={o.id:o.certainty for o in bundle.observations}
    assert before==after
