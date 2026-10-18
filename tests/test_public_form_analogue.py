"""Documented public-reference analogue must be isolated and clearly non-authentic."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from astra_contracts.public_reference_probe import PublicPageNote
from astra_contracts.public_form_analogue import generate_analogue

FIXTURES=Path(__file__).resolve().parents[1] / 'fixtures'
NOTE=FIXTURES/'public_selenium_form_note_20261019.json'
PAGE=FIXTURES/'public_selenium_form_page_excerpt_20261019.txt'
DOCS=FIXTURES/'public_selenium_official_docs_excerpt_20261019.txt'


def good_note():
    return PublicPageNote.model_validate_json(NOTE.read_text(encoding='utf-8'))


@pytest.fixture
def demo():
    import uuid
    root = Path(tempfile.gettempdir())
    candidate = root / ('astra-public-form-' + uuid.uuid4().hex)
    report=generate_analogue(good_note(),PAGE,DOCS,candidate)
    try:
        spec=importlib.util.spec_from_file_location('astra_generated_public_form',candidate/'app.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield candidate,report,TestClient(module.app)
    finally:
        import shutil
        shutil.rmtree(candidate)


def test_form_end_to_end(demo):
    p,r,c=demo
    home=c.get('/')
    assert home.status_code==200 and 'name="my-text"' in home.text
    assert 'method="post" action="/submit"' in home.text
    assert '<button type="submit">Submit</button>' in home.text
    response=c.post('/submit',data={'my-text':'Astra public demo'})
    assert response.status_code==200
    assert '<p id="message">Received!</p>' in response.text
    assert c.get('/health').json()=={'synthetic':True,'status':'ok','original_site_interaction_verified':False}


def test_no_echo_or_source_copy(demo):
    p,r,c=demo
    attack='<script>alert(1)</script>'
    response=c.post('/submit',data={'my-text':attack})
    assert response.status_code==200
    assert attack not in response.text
    assert 'Received!' in response.text
    assert all('selenium.dev/selenium/web/web-form.html' not in (p/name).read_text(encoding='utf-8') for name in ['app.py'])


@pytest.mark.parametrize('data',[
    {},{'my-text':''},{'my-text':'x'*81},
    {'my-text':'ok','secret':'unexpected'},
    {'fake':'ok'},{'my-text':'bad\nnewline'},
])
def test_bad_input(demo,data):
    _,_,c=demo
    if data == {}:
        response = c.post('/submit', content=b'', headers={'Content-Type':'application/x-www-form-urlencoded'})
    else:
        response = c.post('/submit',data=data)
    assert response.status_code==422


def test_duplicate_form_key(demo):
    _,_,c=demo
    assert c.post('/submit',content=b'my-text=a&my-text=b',headers={'Content-Type':'application/x-www-form-urlencoded'}).status_code==422


def test_overlong_payload(demo):
    _,_,c=demo
    r=c.post('/submit',content=b'my-text='+b'a'*1025,headers={'Content-Type':'application/x-www-form-urlencoded'})
    assert r.status_code==413


def test_wrong_media(demo):
    _,_,c=demo
    assert c.post('/submit',json={'my-text':'ok'}).status_code==415


def test_generated_provenance_no_approval(demo):
    directory,report,_=demo
    manifest=json.loads((directory/'provenance.json').read_text(encoding='utf-8'))
    assert manifest['classification']=='public_documentation_based_synthetic_analogue'
    for name in ['original_site_click_executed','original_site_behavior_verified','source_code_copied',
                 'customer_db_or_api_connected','deployment_authorized','ui_mapping_approved']:
        assert manifest[name] is False
    for name,sha in report['generated_file_sha256'].items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==sha
    assert set(report['generated_file_sha256'])=={'app.py','README.md','requirements.txt','provenance.json'}


def test_outside_temp_refused(tmp_path):
    with pytest.raises(ValueError,match='fresh'):
        generate_analogue(good_note(),PAGE,DOCS,tmp_path/'astra-public-form-evil')
    with pytest.raises(ValueError,match='fresh'):
        generate_analogue(good_note(),PAGE,DOCS,tmp_path)


def test_existing_temp_refused():
    with tempfile.TemporaryDirectory(prefix='astra-public-form-') as existing:
        with pytest.raises(ValueError,match='fresh'):
            generate_analogue(good_note(),PAGE,DOCS,Path(existing))


def test_tampered_evidence_before_creating(tmp_path):
    import uuid
    candidate=Path(tempfile.gettempdir())/('astra-public-form-'+uuid.uuid4().hex)
    bad=tmp_path/'tampered.txt'
    bad.write_bytes(PAGE.read_bytes()+b'x')
    with pytest.raises(ValueError,match='SHA-256'):
        generate_analogue(good_note(),bad,DOCS,candidate)
    assert not candidate.exists()


@pytest.mark.parametrize('field,value',[
    ('documented_input_selector','password'),
    ('documented_result_token','Unexpected!'),
    ('input_token','Password'),
    ('submit_token','Reset'),
])
def test_wrong_recipe_rejected_without_files(field,value):
    import uuid
    data=good_note().model_dump()
    data[field]=value
    candidate=Path(tempfile.gettempdir())/('astra-public-form-'+uuid.uuid4().hex)
    with pytest.raises(ValueError):
        generate_analogue(PublicPageNote.model_validate(data),PAGE,DOCS,candidate)
    assert not candidate.exists()


def test_forged_site_verification_rejected():
    data=good_note().model_dump()
    data['original_site_behavior_verified']=True
    with pytest.raises(ValidationError):
        PublicPageNote.model_validate(data)


def test_cli_dry_run_no_files(capsys):
    from scripts.build_public_form_analogue import main
    assert main([]) == 0
    output=json.loads(capsys.readouterr().out)
    assert output['mode']=='dry_run'
    assert output['network_used'] is False
    assert output['local_output_created'] is False


def test_cli_generate_only_temp(monkeypatch,capsys,tmp_path):
    from scripts import build_public_form_analogue as runner
    import shutil
    import uuid
    target=Path(tempfile.gettempdir())/('astra-public-form-'+uuid.uuid4().hex)
    # Patch predictable fresh path via the already tested generator path guard.
    monkeypatch.setattr(runner.uuid,'uuid4',lambda: type('Uuid',(),{'hex':target.name.removeprefix('astra-public-form-')})())
    try:
        assert runner.main(['--generate'])==0
        info=json.loads(capsys.readouterr().out)
        assert info['generated_path']==str(target)
        assert info['manifest']['original_site_click_executed'] is False
        assert (target/'app.py').is_file()
    finally:
        if target.is_dir():shutil.rmtree(target)


def test_documented_module_invocation_dry_run():
    import subprocess,sys
    result=subprocess.run(
        [sys.executable,'-m','scripts.build_public_form_analogue'],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=8,check=True,
    )
    info=json.loads(result.stdout)
    assert info['mode']=='dry_run' and not info['network_used']
