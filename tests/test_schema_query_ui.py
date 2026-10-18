"""Synthetic physical-field query controls must be safe and usable in generated app."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_query_embed import generate_integrated_preview
from astra_contracts.schema_query_extension import QueryPlan
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, SchemaAcceptanceCases
from astra_contracts.schema_crud_embed import embed_synthetic_crud
from astra_contracts.schema_query_ui import embed_query_ui, QUERY_UI_HTML, UI_SOURCE
from astra_contracts.synthetic_generator import APP, HTML

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures'


def load(file, model):
    return model.model_validate_json((FIXTURES/file).read_text(encoding='utf-8'))


@pytest.fixture(scope='module',params=['products','tickets'])
def preview(request):
    kind=request.param
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root=Path(folder)
        generate_integrated_preview(
            load('synthetic_manual_filter_observation_20261019.json',ObservationBundle), FIXTURES,
            load('synthetic_manual_filter_schema_20261019.json',OwnedSchemaDeclaration),
            load('synthetic_generation_request_20261018.json',GenerationRequest),
            load(f'synthetic_reuse_{kind}_table_20261019.json',AlternateSyntheticTable),
            load(f'synthetic_reuse_{kind}_cases_20261019.json',SchemaAcceptanceCases),
            load(f'synthetic_reuse_{kind}_query_cases_20261019.json',QueryPlan), root)
        embed_synthetic_crud(root)
        yield kind,root


@pytest.fixture
def cloned(preview):
    kind,old=preview
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root=Path(folder)
        shutil.copytree(old,root,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3'))
        yield kind,root


def isolated(root,code):
    p=subprocess.run([sys.executable,'-c',code],cwd=root,capture_output=True,text=True,timeout=20)
    assert p.returncode==0,p.stdout+'\n'+p.stderr
    return p.stdout


def test_generated_html_and_api(cloned):
    kind,root=cloned
    protected={n:(root/n).read_bytes() for n in ['app/main.py','app/index.html','app/extended.py','app/full.py','data/seed.json']}
    report=embed_query_ui(root)
    assert report.generated_entrypoint=='app.ui:app'
    assert report.customer_database_connected is False and report.deployment_authorized is False
    assert (root/'app/query_ui.html').read_text(encoding='utf-8')==QUERY_UI_HTML
    assert 'innerHTML' not in QUERY_UI_HTML
    assert 'textContent' in QUERY_UI_HTML
    assert (root/'app/ui.py').read_text().startswith(UI_SOURCE.split('__UI_SHA256__')[0])
    assert (root/'data/query_ui_embed_report.json').is_file()
    for n, original in protected.items():assert (root/n).read_bytes()==original
    assert (root/'app/main.py').read_text()==APP
    assert (root/'app/index.html').read_text()==HTML
    result=isolated(root,'''from app.ui import create_ui_app
from fastapi.testclient import TestClient
app=create_ui_app()
with TestClient(app) as c:
    assert c.get('/preview').status_code==200
    assert c.get('/api/preview-schema').status_code==200
    assert c.get('/health').json()['synthetic'] is True
    assert c.post('/api/items',json={}).status_code==405
    assert c.get('/sandbox/api/items').status_code==404
print('GENERATED_UI_PASS')''')
    assert 'GENERATED_UI_PASS' in result


def test_typed_fields_and_existing_cases(cloned):
    kind,root=cloned
    embed_query_ui(root)
    expected='popularity' if kind=='products' else 'priority'
    output=isolated(root,f'''from app.ui import create_ui_app
from fastapi.testclient import TestClient
with TestClient(create_ui_app()) as c:
 schema=c.get('/api/preview-schema').json()
 assert schema['synthetic'] and schema['original_site_behavior_verified'] is False
 assert any(x['name']=={expected!r} and x['type']=='integer' for x in schema['fields'])
 a=c.get('/api/rows',params={{'sort_by':{expected!r},'direction':'desc'}})
 assert a.status_code==200
 assert c.get('/api/rows',params={{'sort_by':'__proto__'}}).status_code==422
 assert c.get('/api/items').status_code==200
print('TYPED_UI_PASS')''')
    assert 'TYPED_UI_PASS' in output


def test_no_external_path(tmp_path):
    with pytest.raises(ValueError,match='isolated'):
        embed_query_ui(tmp_path)


def test_output_no_overwrite(cloned):
    _,root=cloned
    path=root/'app/ui.py';path.write_text('PRESERVE')
    with pytest.raises(ValueError,match='overwrite'):
        embed_query_ui(root)
    assert path.read_text()=='PRESERVE'


def test_symlink_output_no_overwrite(cloned,tmp_path):
    _,root=cloned
    external=tmp_path/'outside.html';external.write_text('PRESERVE')
    (root/'app/query_ui.html').symlink_to(external)
    with pytest.raises(ValueError,match='overwrite'):
        embed_query_ui(root)
    assert external.read_text()=='PRESERVE'


def test_tamper_prior_code_rejected(cloned):
    _,root=cloned
    (root/'app/full.py').write_text('print("not trusted")')
    with pytest.raises(ValueError,match='untrusted'):
        embed_query_ui(root)
    assert not (root/'app/ui.py').exists()


def test_tamper_prior_report_rejected(cloned):
    _,root=cloned
    p=root/'data/crud_embed_report.json'
    v=json.loads(p.read_text());v['deployment_authorized']=True
    p.write_text(json.dumps(v))
    with pytest.raises(Exception):
        embed_query_ui(root)
    assert not (root/'app/ui.py').exists()


def test_reject_missing_prior_crud(cloned):
    _,root=cloned
    (root/'app/sandbox_crud.py').unlink()
    with pytest.raises(ValueError,match='untrusted'):
        embed_query_ui(root)
    assert not (root/'app/ui.py').exists()


def test_tamper_ui_static_blocked_after_install(cloned):
    _,root=cloned
    embed_query_ui(root)
    (root/'app/query_ui.html').write_text('<script>alert(1)</script>')
    x=isolated(root,'''from app.ui import create_ui_app
from fastapi.testclient import TestClient
with TestClient(create_ui_app()) as c:
 assert c.get('/preview').status_code==503
 assert c.get('/api/preview-schema').status_code==503
print('TAMPER_BLOCKED')''')
    assert 'TAMPER_BLOCKED' in x


def test_crud_keeps_default_off_and_explicit_temp_on(cloned):
    _,root=cloned
    embed_query_ui(root)
    x=isolated(root,'''from app.ui import create_ui_app
from fastapi.testclient import TestClient
base=create_ui_app()
with TestClient(base) as c:
 assert c.get('/sandbox/api/items').status_code==404
 assert c.get('/preview').status_code==200
other=create_ui_app(enable_synthetic_crud=True)
with TestClient(other) as c:
 item={'id':'demo1','title':'fiction','category':'fake','score':12}
 assert c.post('/sandbox/api/items',json=item).status_code==201
 assert c.get('/api/preview-schema').status_code==200
 assert c.get('/api/items').status_code==200
other.state.synthetic_crud_tempdir.cleanup()
print('ISOLATED_WRITES')''')
    assert 'ISOLATED_WRITES' in x


def test_runtime_tampered_physical_fixture_blocked(cloned):
    _,root=cloned
    embed_query_ui(root)
    table=root/'data/query_physical_fixture.json'
    original=json.loads(table.read_text(encoding='utf-8'))
    original['table_name']='unsafe-replaced'
    table.write_text(json.dumps(original),encoding='utf-8')
    run=subprocess.run([sys.executable,'-c','from app.ui import create_ui_app'],
                       cwd=root,capture_output=True,text=True,timeout=20)
    assert run.returncode!=0
    assert 'synthetic query fixture was changed' in run.stderr



def test_ui_route_is_not_original_home(cloned):
    _,root=cloned
    embed_query_ui(root)
    output=isolated(root,'''from fastapi.testclient import TestClient
from app.ui import create_ui_app
with TestClient(create_ui_app()) as c:
 assert 'ASTRA synthetic preview' in c.get('/').text
 assert '데이터 정렬 · 필터 미리보기' in c.get('/preview').text
 assert c.get('/preview').headers['cache-control']=='no-store'
 assert c.get('/preview').headers['x-content-type-options']=='nosniff'
 assert c.get('/api/preview-schema').headers['cache-control']=='no-store'
print('HOME_PRESERVED')''')
    assert 'HOME_PRESERVED' in output
