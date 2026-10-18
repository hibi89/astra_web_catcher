"""Local UI only records unverified opinions; no approval or real DB access."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration, MappingReport
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.reviewer_decisions import ReviewRecord
from astra_contracts.review_ui import create_review_app, _safe_folder

F = Path(__file__).resolve().parents[1] / 'fixtures'

@pytest.fixture
def ui(tmp_path):
    spec=FunctionalSpecDraft.model_validate_json((F/'jp_nail_functional_spec_draft_20261018.json').read_text())
    schema=OwnedSchemaDeclaration.model_validate_json((F/'synthetic_owned_schema_mapping_20261018.json').read_text())
    mapping=MappingReport.model_validate_json((F/'synthetic_mapping_report_20261018.json').read_text())
    with tempfile.TemporaryDirectory(prefix='astra-review-') as storage:
        app=create_review_app(spec,schema,mapping,Path(storage))
        with TestClient(app) as client:
            info=client.get('/api/packet').json()
            yield client,info,Path(storage)


def opinion(item,packet,decision='needs_more_evidence',rationale='원본 캡처와 데이터 출처를 추가 확인해야 합니다.'):
    return {'version':'0.1','packet_sha256':packet['packet_sha256'],
            'reviewer_claimed_label':'테스트 검토자, 미인증',
            'responses':[{'item_id':item['item_id'],'decision':decision,'rationale':rationale}]}


def test_page_and_static_assets_have_local_security_headers(ui):
    c,p,_=ui
    page=c.get('/')
    assert page.status_code==200 and '근거와 필드 의미 검토' in page.text
    assert '승인·실사용 권한이 아닙니다' in page.text
    assert page.headers['cache-control']=='no-store'
    assert "script-src 'self'" in page.headers['content-security-policy']
    assert c.get('/review.js').status_code==200
    assert c.get('/review.css').status_code==200
    assert 'innerHTML' not in c.get('/review.js').text
    assert 'textContent' in c.get('/review.js').text


def test_packet_counts_and_token_not_an_approval(ui):
    c,p,_=ui
    assert len(p['packet']['items'])==13
    assert sum(x['kind']=='observed_behavior' for x in p['packet']['items'])==1
    assert sum(x['kind']=='unresolved_behavior' for x in p['packet']['items'])==2
    assert sum(x['kind']=='field_semantics' for x in p['packet']['items'])==10
    assert not p['authorization_granted'] and not p['packet']['approval_verified']
    assert len(p['review_token'])>20


def test_save_and_reload_one_opinion(ui):
    c,p,folder=ui
    item=next(x for x in p['packet']['items'] if x['kind']=='unresolved_behavior')
    body=opinion(item,p)
    res=c.post('/api/opinions',json=body,headers={'X-Astra-Review-Token':p['review_token']})
    assert res.status_code==200,res.text
    data=res.json()
    assert data['record']['recorded_opinion_count']==1
    assert data['record']['pending_count']==12
    assert data['record']['user_approval_verified'] is False
    assert data['record']['code_generation_authorized'] is False
    assert data['record']['database_access_authorized'] is False
    assert data['record']['deployment_authorized'] is False
    found=list(folder.glob('*.json'))
    assert len(found)==1
    assert ReviewRecord.model_validate_json(found[0].read_text())
    read=c.get('/api/opinions/'+data['record_id'],headers={'X-Astra-Review-Token':p['review_token']})
    assert read.status_code==200
    assert read.json()['record']==data['record']
    assert not read.json()['authorization_granted']


def test_multi_item_save_works(ui):
    c,p,folder=ui
    item=p['packet']['items'][0]
    compatible=next(x for x in p['packet']['items'] if x['mapping_status']=='structurally_compatible_unapproved')
    data=opinion(item,p)
    data['responses'].append({'item_id':compatible['item_id'], 'decision':'supported_as_proposal',
                              'rationale':'데이터 타입은 일치하나 의미 확인이 추가로 필요합니다.'})
    r=c.post('/api/opinions',json=data,headers={'X-Astra-Review-Token':p['review_token']})
    assert r.status_code==200,r.text
    assert r.json()['record']['recorded_opinion_count']==2
    assert not r.json()['record']['field_meanings_verified']

@pytest.mark.parametrize('malicious',[
    'supported_as_proposal', 'authorize_deploy',
])
def test_unknown_behavior_cannot_gain_permissions(ui,malicious):
    c,p,folder=ui
    target=next(x for x in p['packet']['items'] if x['kind']=='unresolved_behavior')
    r=c.post('/api/opinions',json=opinion(target,p,decision=malicious),
             headers={'X-Astra-Review-Token':p['review_token']})
    assert r.status_code==422
    assert not list(folder.iterdir())


def test_archived_behavior_cannot_be_supported(ui):
    c,p,folder=ui
    item=next(x for x in p['packet']['items'] if x['archived_evidence_only'])
    r=c.post('/api/opinions',json=opinion(item,p,decision='supported_as_proposal'),headers={'X-Astra-Review-Token':p['review_token']})
    assert r.status_code==422 and not list(folder.iterdir())


def test_field_with_missing_mapping_cannot_be_supported(ui):
    c,p,folder=ui
    item=next(x for x in p['packet']['items'] if x['mapping_status']=='unmapped')
    r=c.post('/api/opinions',json=opinion(item,p,decision='supported_as_proposal'),headers={'X-Astra-Review-Token':p['review_token']})
    assert r.status_code==422 and not list(folder.iterdir())


def test_stale_packet_and_forged_approval_fail(ui):
    c,p,folder=ui
    item=p['packet']['items'][0]
    body=opinion(item,p)
    body['packet_sha256']='0'*64
    assert c.post('/api/opinions',json=body,headers={'X-Astra-Review-Token':p['review_token']}).status_code==422
    body=opinion(item,p)
    body['approve_deployment']=True
    assert c.post('/api/opinions',json=body,headers={'X-Astra-Review-Token':p['review_token']}).status_code==422
    assert not list(folder.iterdir())


def test_missing_token_or_bad_origin_never_creates_file(ui):
    c,p,folder=ui
    body=opinion(p['packet']['items'][0],p)
    assert c.post('/api/opinions',json=body).status_code==403
    assert c.post('/api/opinions',json=body,headers={'X-Astra-Review-Token':'wrong'}).status_code==403
    assert c.post('/api/opinions',json=body,headers={'Origin':'https://untrusted.example','X-Astra-Review-Token':p['review_token']}).status_code==403
    assert not list(folder.iterdir())


def test_refuse_non_json_and_large_payload(ui):
    c,p,folder=ui
    assert c.post('/api/opinions',data='not json',headers={'X-Astra-Review-Token':p['review_token']}).status_code==415
    assert c.post('/api/opinions',content=b'x'*70000,headers={'X-Astra-Review-Token':p['review_token'],'Content-Type':'application/json'}).status_code==413
    assert not list(folder.iterdir())


def test_retrieval_denies_bad_token_path(ui):
    c,p,folder=ui
    item=p['packet']['items'][0]
    res=c.post('/api/opinions',json=opinion(item,p),headers={'X-Astra-Review-Token':p['review_token']}).json()
    identifier=res['record_id']
    assert c.get('/api/opinions/'+identifier).status_code==403
    assert c.get('/api/opinions/zzzz',headers={'X-Astra-Review-Token':p['review_token']}).status_code==404
    assert c.get('/api/opinions/'+identifier,headers={'X-Astra-Review-Token':'bad'}).status_code==403
    assert len(list(folder.glob('*.json')))==1


def test_review_storage_path_restrictions(tmp_path):
    with pytest.raises(ValueError):
        _safe_folder(tmp_path)
    with tempfile.TemporaryDirectory(prefix='astra-review-') as tempdir:
        assert _safe_folder(Path(tempdir))==Path(tempdir)
        link=Path(tempfile.gettempdir())/'astra-review-unit-link'
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(Path(tempdir), target_is_directory=True)
        try:
            with pytest.raises(ValueError): _safe_folder(link)
        finally: link.unlink()


def test_host_restriction(ui):
    c,p,_=ui
    assert c.get('/api/packet',headers={'Host':'attacker.invalid'}).status_code==403


def test_review_template_shows_all_three_group_labels(ui):
    c,p,_=ui
    js=c.get('/review.js').text
    assert all(s in js for s in ('관찰 기능','미확인 사항','필드 의미'))
    assert 'supported_as_proposal' in js and 'disabled=true' in js


def test_no_db_or_network_client_imports():
    src=(Path(__file__).resolve().parents[1]/'astra_contracts/review_ui.py').read_text()
    assert 'import sqlite3' not in src
    assert 'import requests' not in src
    assert 'subprocess' not in src


def test_multiple_saves_append_only_and_record_ids_distinct(ui):
    c,p,folder=ui
    target=p['packet']['items'][1]
    payload=opinion(target,p)
    headers={'X-Astra-Review-Token':p['review_token']}
    first=c.post('/api/opinions',json=payload,headers=headers)
    second=c.post('/api/opinions',json=payload,headers=headers)
    assert first.status_code==second.status_code==200
    assert first.json()['record_id']!=second.json()['record_id']
    assert len(list(folder.glob('*.json')))==2
    assert all(x['reviewer_identity_verified'] is False for x in [first.json()['record'],second.json()['record']])


def test_ui_keeps_hidden_filter_drafts_and_does_not_request_approval(ui):
    c,_,_=ui
    js=c.get('/review.js').text
    assert 'captureDrafts()' in js and 'for(const [item_id,x] of drafts)' in js
    assert "drafts.set(id" in js
    assert 'authorize_deploy' not in js
    assert 'innerHTML' not in js


def test_invalid_rationale_cannot_be_saved(ui):
    c,p,folder=ui
    item=p['packet']['items'][0]
    submission=opinion(item,p,rationale='no')
    res=c.post('/api/opinions',json=submission,headers={'X-Astra-Review-Token':p['review_token']})
    assert res.status_code==422
    assert list(folder.iterdir())==[]


def test_view_does_not_return_original_user_credentials(ui):
    c,p,_=ui
    page=c.get('/').text
    assert 'access_token' not in page
    assert 'password' not in page.lower()
    assert p['review_token'] not in page
