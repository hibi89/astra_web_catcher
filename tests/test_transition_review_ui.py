"""The before/after evidence ledger must never enable a generated-app control."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import CaptureIntakeRequest, register_captures
from astra_contracts.capture_transition_ledger import TransitionPlan, build_transition_ledger
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.transition_review_ui import (
    DisplayManifest, TRANSITION_HTML, TRANSITION_JS,
    build_display_manifest, embed_transition_review_ui,
)
from tests.test_mapping_review_ui import generated_base, cloned, attach

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'fixtures'


def read(name, cls):
    return cls.model_validate_json((FIXTURES/name).read_bytes())


@pytest.fixture
def registered_pair():
    bundle=read('synthetic_transition_pair_observation_20261019.json',ObservationBundle)
    request=read('synthetic_transition_pair_intake_request_20261019.json',CaptureIntakeRequest)
    plan=read('synthetic_transition_pair_plan_20261019.json',TransitionPlan)
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as folder:
        intake=Path(folder)
        manifest=register_captures(bundle,FIXTURES,request,intake)
        assert fingerprint(manifest)==plan.intake_manifest_sha256
        yield bundle,intake,plan


def test_projection_retains_immutably_disabled_authorities(registered_pair):
    bundle,intake,plan=registered_pair
    ledger=build_transition_ledger(bundle,intake,plan)
    display=build_display_manifest(ledger)
    assert display.source_ledger_sha256==fingerprint(ledger)
    assert display.byte_integrity_checked_at_build
    assert not display.capture_files_rechecked_at_request
    assert not display.original_site_behavior_verified
    assert not display.evidence_authenticity_verified
    assert not display.semantic_approval_granted
    assert not display.ui_controls_enabled
    assert display.fictional_demo_only is True
    assert len(display.findings)==1
    assert display.findings[0].status=='paired_bytes_present_unverified'
    assert not display.findings[0].enabled
    raw=display.model_dump_json()
    assert 'all' not in json.loads(raw)['findings'][0].values()
    assert 'colors' not in json.loads(raw)['findings'][0].values()
    assert 'before_value' not in raw and 'after_value' not in raw
    assert 'before_capture_id' in raw
    assert '<script>' not in raw


@pytest.mark.parametrize('field',[ 'ui_controls_enabled','original_site_behavior_verified',
    'evidence_authenticity_verified','semantic_approval_granted','deployment_authorized',
    'owner_database_access_authorized','capture_files_rechecked_at_request'])
def test_forged_approval_rejected(registered_pair,field):
    b,i,p=registered_pair
    data=build_display_manifest(build_transition_ledger(b,i,p)).model_dump(mode='json')
    data[field]=True
    with pytest.raises(ValidationError): DisplayManifest.model_validate(data)


def test_forged_finding_or_extra_fields_rejected(registered_pair):
    b,i,p=registered_pair
    data=build_display_manifest(build_transition_ledger(b,i,p)).model_dump(mode='json')
    for field in ['enabled','evidence_authenticity_verified','original_site_behavior_verified']:
        bad=copy.deepcopy(data);bad['findings'][0][field]=True
        with pytest.raises(ValidationError):DisplayManifest.model_validate(bad)
    bad=copy.deepcopy(data);bad['findings'][0]['before_value']='private customer text'
    with pytest.raises(ValidationError):DisplayManifest.model_validate(bad)


def test_duplicate_finding_rejected(registered_pair):
    b,i,p=registered_pair
    raw=build_display_manifest(build_transition_ledger(b,i,p)).model_dump(mode='json')
    raw['findings'].append(copy.deepcopy(raw['findings'][0]))
    with pytest.raises(ValidationError,match='duplicate'):DisplayManifest.model_validate(raw)


def run(root,code,env=None):
    result=subprocess.run([sys.executable,'-c',code],cwd=root,env=env,capture_output=True,text=True,timeout=25)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    return result.stdout


@pytest.mark.parametrize('bad', [None,'ledger','html','mapped_html','mapped_manifest'])
def test_generated_transition_page_all_disabled(cloned,registered_pair,bad):
    kind,root=cloned
    attach(kind,root)
    b,i,p=registered_pair
    protected={path:(root/path).read_bytes() for path in [
        'app/main.py','app/index.html','app/ui.py','app/query_ui.html','app/mapped.py',
        'app/mapped_review.html','data/review_manifest.json','data/query_physical_fixture.json']}
    report=embed_transition_review_ui(root,b,i,p)
    assert report.enabled_actions is False
    assert report.entrypoint=='app.transitions:app'
    assert not report.customer_db_connected
    assert (root/'app/transition_review.html').read_text(encoding='utf-8')==TRANSITION_HTML
    assert 'innerHTML' not in TRANSITION_JS
    assert 'textContent' in TRANSITION_JS
    assert 'button.disabled=true' in TRANSITION_JS
    for path,value in protected.items(): assert (root/path).read_bytes()==value
    if bad:
        target={
          'ledger':'data/transition_review_manifest.json',
          'html':'app/transition_review.html',
          'mapped_html':'app/mapped_review.html',
          'mapped_manifest':'data/review_manifest.json',
        }[bad]
        (root/target).write_text('tampered!',encoding='utf-8')
    run(root,'''from fastapi.testclient import TestClient
from app.transitions import create_transition_app
with TestClient(create_transition_app()) as c:
  expected=503 if '''+repr(bool(bad))+''' else 200
  assert c.get('/preview-transitions').status_code==expected
  r=c.get('/api/transition-ledger')
  assert r.status_code==expected
  if not '''+repr(bool(bad))+''':
    data=r.json()
    assert len(data['findings'])==1
    assert data['findings'][0]['status']=='paired_bytes_present_unverified'
    assert all(x['enabled'] is False for x in data['findings'])
    assert data['ui_controls_enabled'] is False
    assert data['original_site_behavior_verified'] is False
    assert c.get('/preview-mapped').status_code==200
    assert c.get('/preview').status_code==200
    assert c.get('/api/review-manifest').status_code==200
    assert c.post('/api/items',json={}).status_code==405
    assert c.get('/sandbox/api/items').status_code==404
    assert c.get('/api/rows',params={'sort_by':'family' if '''+repr(kind)+'''=='products' else 'lane'}).status_code==200
print('DISABLED_TRANSITION_UI_OK')''')


def test_reject_malformed_intake_before_any_write(cloned,registered_pair):
    kind,root=cloned;attach(kind,root)
    b,i,p=registered_pair
    (i/'captures'/'before_dom_fictional.txt').write_text('changed!',encoding='utf-8')
    with pytest.raises(ValueError,match='byte-integrity'):
        embed_transition_review_ui(root,b,i,p)
    assert not (root/'app/transitions.py').exists()


def test_reject_stale_plan_before_any_write(cloned,registered_pair):
    kind,root=cloned;attach(kind,root)
    b,i,p=registered_pair
    raw=p.model_dump(mode='json');raw['original_bundle_sha256']='a'*64
    with pytest.raises(ValueError,match='stale'):
        embed_transition_review_ui(root,b,i,TransitionPlan.model_validate(raw))
    assert not (root/'app/transitions.py').exists()


def test_reject_prior_mapped_source_tampering(cloned,registered_pair):
    kind,root=cloned;attach(kind,root)
    (root/'app/mapped.py').write_text('tamper',encoding='utf-8')
    b,i,p=registered_pair
    with pytest.raises(ValueError,match='tampered'):
        embed_transition_review_ui(root,b,i,p)
    assert not (root/'app/transitions.py').exists()


def test_reject_preexisting_output(cloned,registered_pair):
    kind,root=cloned;attach(kind,root)
    path=root/'app/transition_review.html';path.write_text('ORIGINAL',encoding='utf-8')
    b,i,p=registered_pair
    with pytest.raises(ValueError,match='already exists'):
        embed_transition_review_ui(root,b,i,p)
    assert path.read_text()=='ORIGINAL'
    assert not (root/'app/transitions.py').exists()


def test_reject_arbitrary_destination(tmp_path,registered_pair):
    b,i,p=registered_pair
    with pytest.raises(ValueError,match='isolated'):
        embed_transition_review_ui(tmp_path,b,i,p)


def test_write_enabled_mode_refused(cloned,registered_pair):
    kind,root=cloned;attach(kind,root)
    b,i,p=registered_pair;embed_transition_review_ui(root,b,i,p)
    env=dict(os.environ,ASTRA_ENABLE_SYNTHETIC_CRUD='YES_TEMP_ONLY')
    probe=subprocess.run([sys.executable,'-c','import app.transitions'],cwd=root,
                         env=env,text=True,capture_output=True,timeout=20)
    assert probe.returncode!=0
    assert 'write-enabled' in probe.stderr
