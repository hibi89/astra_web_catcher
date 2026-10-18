"""Real generated synthetic project: protected original API, optional CRUD only."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_query_embed import generate_integrated_preview
from astra_contracts.schema_query_extension import QueryPlan
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, SchemaAcceptanceCases
from astra_contracts.schema_crud_embed import embed_synthetic_crud, CRUD_SOURCE
from astra_contracts.synthetic_generator import APP, HTML

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'


def load(file, model):
    return model.model_validate_json((FIXTURES / file).read_text(encoding='utf-8'))


@pytest.fixture(scope='module', params=['products','tickets'])
def built_preview(request):
    kind = request.param
    bundle = load('synthetic_manual_filter_observation_20261019.json', ObservationBundle)
    canonical_schema = load('synthetic_manual_filter_schema_20261019.json', OwnedSchemaDeclaration)
    gen_request = load('synthetic_generation_request_20261018.json', GenerationRequest)
    physical = load(f'synthetic_reuse_{kind}_table_20261019.json', AlternateSyntheticTable)
    acceptance = load(f'synthetic_reuse_{kind}_cases_20261019.json', SchemaAcceptanceCases)
    query = load(f'synthetic_reuse_{kind}_query_cases_20261019.json', QueryPlan)
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root = Path(folder)
        generate_integrated_preview(bundle, FIXTURES, canonical_schema, gen_request,
                                    physical, acceptance, query, root)
        yield kind, root


@pytest.fixture
def clone_preview(built_preview):
    kind, source = built_preview
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root = Path(folder)
        shutil.copytree(source, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.sqlite3', '__pycache__', '.pytest_cache'))
        yield kind, root


def run(root: Path, code: str) -> str:
    p = subprocess.run([sys.executable, '-c', code], cwd=root,
                       capture_output=True, text=True, timeout=15)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout.strip()


def test_embeds_and_executes_crud_only_if_opted_in(clone_preview):
    kind, root = clone_preview
    protected = {rel: (root / rel).read_bytes() for rel in (
        'app/main.py', 'app/index.html', 'app/extended.py', 'data/seed.json')}
    result = embed_synthetic_crud(root)
    assert result.status == 'synthetic_crud_opt_in_integrated_passed'
    assert result.write_routes_off_by_default and result.disposable_sqlite_only
    assert not result.customer_database_connected and not result.deployment_authorized
    assert (root / 'app/sandbox_crud.py').read_text() == CRUD_SOURCE
    assert (root / 'data/crud_embed_report.json').is_file()
    for rel, contents in protected.items():
        assert (root / rel).read_bytes() == contents
    assert (root / 'app/main.py').read_text() == APP
    assert (root / 'app/index.html').read_text() == HTML
    out = run(root, '''from app.full import create_full_app
from fastapi.testclient import TestClient
app=create_full_app(enable_synthetic_crud=True)
with TestClient(app) as c:
 x={'id':'sample','title':'demo','category':'fiction','score':4}
 assert c.post('/sandbox/api/items',json=x).status_code==201
 assert c.patch('/sandbox/api/items/sample',json={'score':9}).json()['score']==9
 assert c.get('/sandbox/api/items/sample').json()['score']==9
 assert c.get('/api/items').status_code==200
 assert c.get('/api/rows',params={'sort_by':''' + repr('popularity' if kind == 'products' else 'priority') + '''}).status_code==200
 assert c.delete('/sandbox/api/items/sample').status_code==204
 assert c.get('/sandbox/api/items').json()==[]
app.state.synthetic_crud_tempdir.cleanup()
print('CRUD_200_201_204_200')''')
    assert out == 'CRUD_200_201_204_200'


def test_default_and_invalid_inputs(clone_preview):
    _, root = clone_preview
    embed_synthetic_crud(root)
    assert run(root, '''from app.full import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
 assert c.get('/sandbox/api/items').status_code==404
 assert c.post('/api/items',json={}).status_code==405
 assert c.get('/health').json()['synthetic'] is True
print('OFF')''') == 'OFF'


def test_no_overwrite(clone_preview):
    _, root = clone_preview
    (root / 'app/full.py').write_text('PRESERVE')
    with pytest.raises(ValueError, match='overwritten'):
        embed_synthetic_crud(root)
    assert (root / 'app/full.py').read_text() == 'PRESERVE'


def test_no_external_paths(tmp_path):
    with pytest.raises(ValueError, match='isolated'):
        embed_synthetic_crud(tmp_path)


def test_invalid_extension_rejected_before_write(clone_preview):
    _, root = clone_preview
    (root / 'data/query_physical_fixture.json').write_text('{}')
    with pytest.raises(Exception):
        embed_synthetic_crud(root)
    assert not (root / 'app/full.py').exists()


def test_tampered_query_source_rejected(clone_preview):
    _, root = clone_preview
    (root / 'app/extended.py').write_text('print("tampered")')
    with pytest.raises(ValueError, match='trusted generated template'):
        embed_synthetic_crud(root)
    assert not (root / 'app/full.py').exists()


def test_symlink_output_not_overwritten(clone_preview, tmp_path):
    _, root = clone_preview
    external = tmp_path / 'external.txt'
    external.write_text('PRESERVE')
    (root / 'app/full.py').symlink_to(external)
    with pytest.raises(ValueError, match='overwritten'):
        embed_synthetic_crud(root)
    assert external.read_text() == 'PRESERVE'


def test_forged_query_authority_is_rejected(clone_preview):
    import json
    _, root = clone_preview
    report = root / 'data/query_embed_report.json'
    payload = json.loads(report.read_text(encoding='utf-8'))
    payload['deployment_authorized'] = True
    report.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(Exception):
        embed_synthetic_crud(root)
    assert not (root / 'app/full.py').exists()


def test_symlinked_query_source_is_rejected(clone_preview, tmp_path):
    _, root = clone_preview
    source = root / 'app/extended.py'
    outside = tmp_path / 'out.py'
    outside.write_bytes(source.read_bytes())
    source.unlink();source.symlink_to(outside)
    with pytest.raises(ValueError, match='symlinked'):
        embed_synthetic_crud(root)
    assert not (root / 'app/full.py').exists()
