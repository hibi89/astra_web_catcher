"""Second Selenium-documented independent local control; real site not touched."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astra_contracts import public_checkbox_analogue as a


def fresh():
    return Path(tempfile.gettempdir()) / ('astra-public-checkbox-' + uuid.uuid4().hex)


@pytest.fixture
def built():
    folder = fresh()
    report = a.generate_checkbox_analogue(a.FIXTURE, folder)
    try:
        spec = importlib.util.spec_from_file_location('independent_checkbox', folder/'app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield folder, report, TestClient(module.app)
    finally:
        shutil.rmtree(folder)


def test_local_readonly_routes_and_provenance(built):
    folder, manifest, client = built
    html = client.get('/')
    assert html.status_code == 200
    assert 'name="checkbox_input" checked' in html.text
    assert '<p id="selection-state" role="status" aria-live="polite">Checked</p>' in html.text
    assert 'script src="/controller.js"' in html.text
    assert "default-src 'none'; script-src 'self'" in html.headers['content-security-policy']
    assert client.get('/controller.js').status_code == 200
    assert client.get('/health').json()['original_site_click_verified'] is False
    assert client.post('/').status_code == 405
    assert client.post('/controller.js').status_code == 405
    assert 'selenium.dev' not in (folder/'app.py').read_text()
    for k in ('original_site_click_executed','original_initial_state_verified',
              'original_site_behavior_verified','source_code_copied',
              'customer_db_or_api_connected','deployment_authorized'):
        assert manifest[k] is False
    assert manifest['generation_contract'] == 'blocked_pending_review'
    for name, digest in manifest['generated_file_sha256'].items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == digest
    assert json.loads((folder/'provenance.json').read_text())['evidence_sha256'] == a.EXCERPT_SHA256


def test_js_checked_unchecked_checked_in_node(built):
    _,_,client = built
    code = client.get('/controller.js').text
    harness = '''const vm=require('node:vm');
const box={checked:true, addEventListener(kind,handler){if(kind!=='change')throw Error(kind);this.change=handler}};
const state={textContent:'Checked'};
vm.runInNewContext(process.argv[1], {document:{getElementById:(id)=>{
if(id==='checkbox_input')return box;if(id==='selection-state')return state;throw Error(id)}}}, {timeout:1000});
if(state.textContent!=='Checked')throw Error('initial');
box.checked=false;box.change();if(state.textContent!=='Unchecked')throw Error('unchecked');
box.checked=true;box.change();if(state.textContent!=='Checked')throw Error('rechecked');
'''
    run = subprocess.run(['node','-e',harness,code],capture_output=True,text=True,timeout=5)
    assert run.returncode == 0, run.stderr


@pytest.mark.parametrize('bad', [b'changed', b'\x00'])
def test_tampered_evidence_rejected_before_create(tmp_path,bad):
    path=tmp_path/'tampered.txt'
    path.write_bytes(a.FIXTURE.read_bytes()+bad)
    dest=fresh()
    with pytest.raises(ValueError,match='SHA-256'):
        a.generate_checkbox_analogue(path,dest)
    assert not dest.exists()


def test_missing_evidence_fails_closed(tmp_path):
    target=fresh()
    with pytest.raises(ValueError, match='missing'):
        a.generate_checkbox_analogue(tmp_path/'absent', target)
    assert not target.exists()


def test_symlink_evidence_refused(tmp_path):
    link=tmp_path/'link'
    link.symlink_to(a.FIXTURE)
    with pytest.raises(ValueError,match='symlinked'):
        a.generate_checkbox_analogue(link,fresh())


def test_existing_output_refused():
    with tempfile.TemporaryDirectory(prefix='astra-public-checkbox-') as path:
        with pytest.raises(ValueError,match='fresh'):
            a.generate_checkbox_analogue(a.FIXTURE,Path(path))


def test_outside_temp_refused(tmp_path):
    target=tmp_path/'astra-public-checkbox-not-temp'
    with pytest.raises(ValueError,match='fresh'):
        a.generate_checkbox_analogue(a.FIXTURE,target)
    assert not target.exists()


def test_cli_dry_run_no_files(capsys):
    assert a.main([])==0
    data=json.loads(capsys.readouterr().out)
    assert data['network_used'] is False and data['local_output_created'] is False
    assert data['mode']=='dry_run'


def test_cli_generate_to_temp(monkeypatch,capsys):
    dest=fresh()
    monkeypatch.setattr(a.uuid,'uuid4',lambda: type('Uuid',(),{'hex':dest.name.split('astra-public-checkbox-')[1]})())
    try:
        assert a.main(['--generate'])==0
        result=json.loads(capsys.readouterr().out)
        assert result['generated_path']==str(dest)
        assert (dest/'app.py').is_file()
    finally:
        if dest.exists(): shutil.rmtree(dest)


def test_cli_module_invocation():
    r=subprocess.run([sys.executable,'-m','astra_contracts.public_checkbox_analogue'],
                     cwd=a.ROOT,capture_output=True,text=True,timeout=5)
    assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)['mode']=='dry_run'
