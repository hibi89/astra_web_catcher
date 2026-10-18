"""Synthetic untrusted file transfer cannot authorize an original data action."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration, MappingReport
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import fingerprint
from astra_contracts.reviewer_decisions import (ReviewPacket, ReviewSubmission,
                                                record_opinions, build_packet)
from astra_contracts.review_transfer import (MAX_TRANSFER_BYTES, ReviewTransferBundle,
                                             export_bundle, import_bundle, validate_record, main)
from astra_contracts.review_ui import create_review_app

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


@pytest.fixture
def packet_record():
    spec = FunctionalSpecDraft.model_validate_json((FIX/'jp_nail_functional_spec_draft_20261018.json').read_text())
    schema = OwnedSchemaDeclaration.model_validate_json((FIX/'synthetic_owned_schema_mapping_20261018.json').read_text())
    report = MappingReport.model_validate_json((FIX/'synthetic_mapping_report_20261018.json').read_text())
    packet = build_packet(spec, schema, report)
    item = next(x for x in packet.items if x.kind.value == 'unresolved_behavior')
    response = ReviewSubmission.model_validate({
        'version':'0.1', 'packet_sha256':fingerprint(packet), 'reviewer_claimed_label':'미인증 검토자',
        'responses':[{'item_id':item.item_id, 'decision':'needs_more_evidence',
                      'rationale':'추가 화면 녹화와 원본 산식을 확인해야 합니다.'}],
    })
    return packet, record_opinions(packet, response), spec, schema, report


def test_roundtrip_and_non_authorization(packet_record):
    p, r, *_ = packet_record
    bundle=export_bundle(p,r)
    result=import_bundle(p,bundle.model_dump_json().encode())
    assert result == r
    assert bundle.record_sha256 == fingerprint(r)
    assert not bundle.approval_granted and not bundle.identity_verified
    assert not bundle.db_access_authorized and not bundle.code_generation_authorized
    assert not bundle.deployment_authorized and not result.user_approval_verified


def test_deterministic_byte_serialization(packet_record):
    p,r,*_=packet_record
    assert export_bundle(p,r).model_dump_json()==export_bundle(p,r).model_dump_json()

@pytest.mark.parametrize('field,value',[
    ('approval_granted', True), ('identity_verified', True),
    ('db_access_authorized', True), ('code_generation_authorized', True),
    ('deployment_authorized', True), ('purpose', 'approve'), ('version', '0.2'),
])
def test_forged_approval_or_mode_fails(packet_record,field,value):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json');body[field]=value
    with pytest.raises(ValidationError):import_bundle(p,json.dumps(body).encode())


def test_extraneous_permission_flag_fails(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json');body['allow_all_writes']=True
    with pytest.raises(ValidationError):import_bundle(p,json.dumps(body).encode())


def test_changed_record_without_matching_digest_fails(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json')
    body['record']['reviewer_claimed_label']='다른 사람'
    with pytest.raises(ValueError,match='digest mismatch'):import_bundle(p,json.dumps(body).encode())


def test_self_consistent_changed_count_still_fails(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json')
    body['record']['pending_count']=100
    from astra_contracts.reviewer_decisions import ReviewRecord
    body['record_sha256']=fingerprint(ReviewRecord.model_validate(body['record']))
    with pytest.raises(ValueError,match='contradicts'):import_bundle(p,json.dumps(body).encode())


def test_self_consistent_forged_support_rejected(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json')
    for item in body['record']['items']:
        if item['review_state']=='recorded_opinion':
            item['reviewer_opinion']='supported_as_proposal'
    from astra_contracts.reviewer_decisions import ReviewRecord
    body['record_sha256']=fingerprint(ReviewRecord.model_validate(body['record']))
    with pytest.raises(ValueError,match='unknown behavior'):import_bundle(p,json.dumps(body).encode())


def test_unknown_evidence_reference_fails_with_resigned_hash(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json')
    row=next(i for i in body['record']['items'] if i['review_state']=='recorded_opinion')
    row['evidence_refs_checked']=['invented_ref']
    from astra_contracts.reviewer_decisions import ReviewRecord
    body['record_sha256']=fingerprint(ReviewRecord.model_validate(body['record']))
    with pytest.raises(ValueError,match='evidence'):import_bundle(p,json.dumps(body).encode())


def test_forged_record_identity_and_missing_item_rejected(packet_record):
    p,r,*_=packet_record
    body=export_bundle(p,r).model_dump(mode='json')
    body['record']['items']=body['record']['items'][:-1]
    from astra_contracts.reviewer_decisions import ReviewRecord
    body['record_sha256']=fingerprint(ReviewRecord.model_validate(body['record']))
    with pytest.raises(ValueError,match='contradicts'):import_bundle(p,json.dumps(body).encode())


def test_wrong_packet_and_stale_source_rejected(packet_record):
    p,r,*_=packet_record
    b=export_bundle(p,r).model_dump(mode='json')
    b['source_packet_sha256']='0'*64
    with pytest.raises(ValueError,match='different/stale'):import_bundle(p,json.dumps(b).encode())
    altered=p.model_copy(deep=True)
    altered.items[0].description='CHANGED SOURCE'
    with pytest.raises(ValueError,match='different/stale'):import_bundle(altered,export_bundle(p,r).model_dump_json().encode())


def test_truncated_invalid_and_large_payloads_rejected(packet_record):
    p,r,*_=packet_record
    for content in (b'not json',b'{"broken"', b'x'*(MAX_TRANSFER_BYTES+1)):
        with pytest.raises((ValueError,ValidationError)):import_bundle(p,content)


def test_record_without_claimed_reviewer_fails(packet_record):
    p,r,*_=packet_record
    bad=r.model_copy(update={'reviewer_claimed_label':None})
    with pytest.raises(ValueError,match='missing claimed'):export_bundle(p,bad)


def test_no_user_consent_in_any_outputs(packet_record):
    p,r,*_=packet_record
    bundle=export_bundle(p,r).model_dump(mode='json')
    assert bundle['record']['user_approval_verified'] is False
    assert bundle['record']['database_access_authorized'] is False
    assert bundle['record']['deployment_authorized'] is False


def test_command_line_valid_and_corrupted(packet_record,tmp_path,capsys):
    p,r,*_=packet_record
    packet_file=tmp_path/'packet.json';packet_file.write_text(p.model_dump_json())
    bundle_file=tmp_path/'bundle.json';bundle_file.write_text(export_bundle(p,r).model_dump_json())
    assert main([str(packet_file),str(bundle_file)])==0
    output=json.loads(capsys.readouterr().out)
    assert output['valid_for_current_packet'] and not output['authenticated']
    bundle_file.write_text('malformed')
    assert main([str(packet_file),str(bundle_file)])==1
    assert capsys.readouterr().err.startswith('FAIL:')


def test_ui_export_import_roundtrip_and_no_user_grants(packet_record):
    p,r,spec,schema,report=packet_record
    with tempfile.TemporaryDirectory(prefix='astra-review-') as storage:
        app=create_review_app(spec,schema,report,Path(storage))
        with TestClient(app) as c:
            info=c.get('/api/packet').json();token=info['review_token']
            item=next(x for x in p.items if x.kind.value=='unresolved_behavior')
            submission={'version':'0.1','packet_sha256':fingerprint(p),
                        'reviewer_claimed_label':'미인증 검토자',
                        'responses':[{'item_id':item.item_id,'decision':'needs_more_evidence',
                                      'rationale':'추가 화면 녹화와 원본 산식을 확인해야 합니다.'}]}
            headers={'X-Astra-Review-Token':token}
            saved=c.post('/api/opinions',json=submission,headers=headers)
            assert saved.status_code==200
            rid=saved.json()['record_id']
            exported=c.get('/api/export/'+rid,headers=headers)
            assert exported.status_code==200
            assert 'attachment;' in exported.headers['content-disposition']
            assert 'review_token' not in exported.text
            imported=c.post('/api/import',content=exported.content,
                            headers={**headers,'Content-Type':'application/json'})
            assert imported.status_code==200,imported.text
            assert imported.json()['record_id']!=rid
            assert imported.json()['record']==saved.json()['record']
            assert imported.json()['authorization_granted'] is False
            assert len(list(Path(storage).glob('*.json')))==2


def test_ui_import_auth_origin_size_and_invalid_contents(packet_record):
    p,r,spec,schema,report=packet_record
    with tempfile.TemporaryDirectory(prefix='astra-review-') as storage:
        app=create_review_app(spec,schema,report,Path(storage))
        with TestClient(app) as c:
            token=c.get('/api/packet').json()['review_token']
            content=export_bundle(p,r).model_dump_json().encode()
            assert c.post('/api/import',content=content,headers={'Content-Type':'application/json'}).status_code==403
            assert c.post('/api/import',content=content,headers={'Content-Type':'application/json','X-Astra-Review-Token':token,'Origin':'https://attacker.example'}).status_code==403
            assert c.post('/api/import',content=content,headers={'X-Astra-Review-Token':token,'Content-Type':'text/plain'}).status_code==415
            assert c.post('/api/import',content=b'x'*(MAX_TRANSFER_BYTES+1),headers={'X-Astra-Review-Token':token,'Content-Type':'application/json'}).status_code==413
            assert c.post('/api/import',content=b'{}',headers={'X-Astra-Review-Token':token,'Content-Type':'application/json'}).status_code==422
            assert list(Path(storage).iterdir())==[]


def test_ui_export_requires_auth_and_avoids_path_escape(packet_record):
    p,r,spec,schema,report=packet_record
    with tempfile.TemporaryDirectory(prefix='astra-review-') as storage:
        app=create_review_app(spec,schema,report,Path(storage))
        with TestClient(app) as c:
            tok=c.get('/api/packet').json()['review_token']
            assert c.get('/api/export/not-a-valid-id',headers={'X-Astra-Review-Token':tok}).status_code==404
            assert c.get('/api/export/'+'0'*24,headers={'X-Astra-Review-Token':tok}).status_code==404
            assert c.get('/api/export/'+'0'*24).status_code==403


def test_review_ui_has_no_external_service_or_permission_grants():
    path=Path(__file__).resolve().parents[1]/'astra_contracts/review_transfer.py'
    source=path.read_text()
    assert not any(s in source for s in ('requests.get(', 'subprocess.run(', 'sqlite3.connect(', 'os.system('))
