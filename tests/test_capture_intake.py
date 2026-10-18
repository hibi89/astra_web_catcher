"""Offline capture intake: file integrity is not human/screenshot authenticity."""
from __future__ import annotations

import base64
import copy
import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import (
    CaptureIntakeRequest, CaptureIntakeManifest, register_captures,
    verify_captures, main,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRVsAAAAASUVORK5CYII=')


def mkbundle():
    return ObservationBundle.model_validate({
        'schema_version':'1.0', 'site_url':'https://example.org/sample',
        'scope':'Synthetic capture submission example; never live website proof',
        'recorded_at':'2026-10-18T12:01:00+09:00',
        'evidence':[],
        'observations':[
            {'id':'sample_filter','feature':'filter','title':'Synthetic example',
             'claim':'A manual capture is proposed for later human inspection.',
             'certainty':'inferred','evidence_ids':[], 'action':None,'before':{},'after':{}},
            {'id':'sample_search','feature':'search','title':'Unverified search',
             'claim':'No real site interaction observed.', 'certainty':'unknown',
             'evidence_ids':[], 'action':None,'before':{},'after':{}}
        ],
    })


def request_for(bundle, captures=None):
    if captures is None:
        captures=[{'evidence': {'id':'capture_png', 'kind':'screenshot',
            'source_ref':'evidence/synthetic_sample.png',
            'captured_at':'2026-10-18T12:02:00+09:00','notes':'Generated synthetic pixel, not a real screenshot'},
            'observation_ids':['sample_filter']}]
    return CaptureIntakeRequest.model_validate({
        'version':'0.1','source_kind':'manually_supplied_local_files',
        'observation_sha256':fingerprint(bundle),'captures':captures,
    })


@pytest.fixture
def work(tmp_path):
    src = tmp_path / 'staged'
    (src/'evidence').mkdir(parents=True)
    (src/'evidence'/'synthetic_sample.png').write_bytes(PNG)
    (src/'evidence'/'safe_dom.txt').write_text('SYNTHETIC UI FILTER ONLY; no real website seen',encoding='utf-8')
    bundle=mkbundle()
    req=request_for(bundle)
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as folder:
        yield bundle,src,req,Path(folder)


def test_register_and_verify_untrusted(work):
    bundle,src,req,out=work
    original=fingerprint(bundle)
    registered=register_captures(bundle,src,req,out)
    assert fingerprint(bundle)==original
    assert registered.status=='pending_manual_evidence_review'
    assert registered.original_bundle_sha256==original
    assert registered.entries[0].evidence.id=='capture_png'
    assert registered.entries[0].proposal_observation_ids==['sample_filter']
    assert (out/'captures/capture_png.png').read_bytes()==PNG
    assert registered.model_dump(mode='json')==CaptureIntakeManifest.model_validate_json((out/'capture_intake.json').read_text()).model_dump(mode='json')
    assert not registered.original_site_behavior_verified
    assert not registered.screenshot_authenticity_verified
    assert not registered.user_approval_verified
    assert not registered.database_access_authorized
    assert verify_captures(bundle,out).result=='bytes_match_untrusted'
    assert verify_captures(bundle,out).bytes_matching==1


def test_two_different_kinds_and_multiple_observation_ids(work):
    bundle,src,req,out=work
    captures=[x.model_dump(mode='json') for x in req.captures]
    captures.append({'evidence': {'id':'capture_dom','kind':'dom_text','source_ref':'evidence/safe_dom.txt',
                     'captured_at':'2026-10-18T12:02:03+09:00','notes':'synthetic DOM text'},
                     'observation_ids':['sample_filter','sample_search']})
    req=request_for(bundle,captures)
    reg=register_captures(bundle,src,req,out)
    assert len(reg.entries)==2
    report=verify_captures(bundle,out)
    assert report.captured_file_count==report.bytes_matching==2
    assert all(x['result']=='bytes_match_untrusted' for x in report.findings)


def test_changed_file_detected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    (out/'captures/capture_png.png').write_bytes(PNG+b'changed')
    assert verify_captures(bundle,out).findings[0]['result']=='size_mismatch'


def test_same_size_modified_detected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    altered=bytearray(PNG)
    altered[-1]^=1
    (out/'captures/capture_png.png').write_bytes(altered)
    assert verify_captures(bundle,out).findings[0]['result']=='hash_mismatch'


def test_missing_file_detected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    (out/'captures/capture_png.png').unlink()
    assert verify_captures(bundle,out).result=='evidence_incomplete'
    assert verify_captures(bundle,out).findings[0]['result']=='missing_file'


def test_symlinked_saved_file_rejected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    path=out/'captures/capture_png.png'
    path.unlink()
    path.symlink_to(src/'evidence/synthetic_sample.png')
    assert verify_captures(bundle,out).findings[0]['result']=='rejected_unsafe_file'


def test_unexpected_existing_file_never_overwritten(work):
    bundle,src,req,out=work
    (out/'important.txt').write_text('PRESERVE')
    with pytest.raises(ValueError,match='empty'):
        register_captures(bundle,src,req,out)
    assert (out/'important.txt').read_text()=='PRESERVE'


def test_preflight_fails_before_any_output(work):
    bundle,src,req,out=work
    (src/'evidence/synthetic_sample.png').unlink()
    with pytest.raises(FileNotFoundError):
        register_captures(bundle,src,req,out)
    assert list(out.iterdir())==[]


def test_stale_bundle_hash_rejected(work):
    bundle,src,req,out=work
    modified=bundle.model_copy(update={'scope':'Different scope'})
    with pytest.raises(ValueError,match='stale'):
        register_captures(modified,src,req,out)
    assert not list(out.iterdir())


def test_verification_wrong_bundle_rejected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    modified=bundle.model_copy(update={'scope':'Different scope'})
    with pytest.raises(ValueError,match='different observation'):
        verify_captures(modified,out)


def test_existing_evidence_id_collision(work):
    bundle,src,req,out=work
    modified=bundle.model_copy(update={'evidence':[req.captures[0].evidence]})
    req2=request_for(modified)
    with pytest.raises(ValueError,match='collides'):
        register_captures(modified,src,req2,out)


def test_unknown_observation_id(work):
    bundle,src,req,out=work
    data=req.model_dump(mode='json')
    data['captures'][0]['observation_ids']=['does_not_exist']
    with pytest.raises(ValueError,match='unknown observation'):
        register_captures(bundle,src,CaptureIntakeRequest.model_validate(data),out)


def test_unsafe_source_ref(work):
    bundle,src,req,out=work
    data=req.model_dump(mode='json')
    data['captures'][0]['evidence']['source_ref']='../outside.png'
    with pytest.raises((ValidationError,ValueError)):
        register_captures(bundle,src,CaptureIntakeRequest.model_validate(data),out)


def test_fake_png_header(work):
    bundle,src,req,out=work
    (src/'evidence/synthetic_sample.png').write_bytes(b'not-a-png')
    with pytest.raises(ValueError,match='PNG'):
        register_captures(bundle,src,req,out)


def test_sensitive_text_rejected(work):
    bundle,src,req,out=work
    (src/'evidence/safe_dom.txt').write_text('Authorization: Bearer abc123',encoding='utf-8')
    capture={'evidence':{'id':'capture_dom','kind':'dom_text','source_ref':'evidence/safe_dom.txt',
                'captured_at':'2026-10-18T12:03:00+09:00','notes':''},'observation_ids':['sample_filter']}
    with pytest.raises(ValueError,match='credentials'):
        register_captures(bundle,src,request_for(bundle,[capture]),out)


def test_archived_report_cannot_be_imported_as_new_capture(work):
    bundle,src,req,out=work
    data=req.model_dump(mode='json')
    data['captures'][0]['evidence']['kind']='archived_report'
    with pytest.raises(ValidationError,match='archived reports'):
        CaptureIntakeRequest.model_validate(data)


def test_duplicate_id_and_path_rejected(work):
    bundle,src,req,out=work
    data=req.model_dump(mode='json')
    data['captures'].append(copy.deepcopy(data['captures'][0]))
    with pytest.raises(ValidationError,match='duplicate'):
        CaptureIntakeRequest.model_validate(data)
    data['captures'][1]['evidence']['id']='other_capture'
    with pytest.raises(ValidationError,match='duplicate'):
        CaptureIntakeRequest.model_validate(data)


def test_duplicate_observation_id_rejected(work):
    bundle,src,req,out=work
    data=req.model_dump(mode='json')
    data['captures'][0]['observation_ids']=['sample_filter','sample_filter']
    with pytest.raises(ValidationError,match='duplicate'):
        CaptureIntakeRequest.model_validate(data)


@pytest.mark.parametrize('flag',[
    'screenshot_authenticity_verified','original_site_behavior_verified','formula_verified',
    'user_approval_verified','code_generation_authorized','database_access_authorized','deployment_authorized'
])
def test_manifest_cannot_claim_approval(work,flag):
    bundle,src,req,out=work
    m=register_captures(bundle,src,req,out).model_dump(mode='json')
    m[flag]=True
    with pytest.raises(ValidationError):
        CaptureIntakeManifest.model_validate(m)


def test_manifest_path_tamper_rejected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    m=json.loads((out/'capture_intake.json').read_text())
    m['entries'][0]['stored_ref']='captures/other.png'
    (out/'capture_intake.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='path'):
        verify_captures(bundle,out)


def test_manifest_link_tamper_rejected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    m=json.loads((out/'capture_intake.json').read_text())
    m['entries'][0]['proposal_observation_ids']=['unknown']
    (out/'capture_intake.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='invalid observation'):
        verify_captures(bundle,out)


def test_cli_register_verify_and_read_only_source(work,tmp_path,capsys):
    bundle,src,req,out=work
    bf=tmp_path/'bundle.json'; rf=tmp_path/'request.json'
    bf.write_text(bundle.model_dump_json());rf.write_text(req.model_dump_json())
    original=(src/'evidence/synthetic_sample.png').read_bytes()
    assert main(['register',str(bf),str(src),str(rf),str(out)])==0
    reg=json.loads(capsys.readouterr().out)
    assert reg['status']=='pending_manual_evidence_review'
    assert main(['verify',str(bf),str(out)])==0
    report=json.loads(capsys.readouterr().out)
    assert report['bytes_matching']==1
    assert (src/'evidence/synthetic_sample.png').read_bytes()==original


def test_invalid_output_folder(work,tmp_path):
    bundle,src,req,out=work
    with pytest.raises(ValueError,match='destination'):
        register_captures(bundle,src,req,tmp_path)


def test_unsupported_status_field(work):
    bundle,src,req,out=work
    d=req.model_dump(mode='json')
    d['approve']=True
    with pytest.raises(ValidationError):
        CaptureIntakeRequest.model_validate(d)


def test_missing_manifest_rejected(work):
    bundle,src,req,out=work
    with pytest.raises(ValueError,match='missing'):
        verify_captures(bundle,out)


def test_oversized_manifest_rejected(work):
    bundle,src,req,out=work
    register_captures(bundle,src,req,out)
    (out/'capture_intake.json').write_text('x'*(256*1024+1))
    with pytest.raises(ValueError,match='oversized'):
        verify_captures(bundle,out)
