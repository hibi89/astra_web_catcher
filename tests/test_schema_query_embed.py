"""Tests that sorting/filtering actually runs INSIDE isolated generated app."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest, fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_query_embed import (
    EmbeddedQueryReport, EXTENDED_SOURCE, GENERATED_TEST, _added_files,
    embed_in_preview, generate_integrated_preview, main,
)
from astra_contracts.schema_query_extension import QueryPlan, verify_query_plan
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, SchemaAcceptanceCases, run_schema_reuse
from astra_contracts.synthetic_generator import APP, HTML

F = Path(__file__).resolve().parents[1] / 'fixtures'


def read(name, model):
    return model.model_validate_json((F / name).read_text(encoding='utf-8'))


def inputs(kind='products'):
    return (
        read('synthetic_manual_filter_observation_20261019.json', ObservationBundle),
        read('synthetic_manual_filter_schema_20261019.json', OwnedSchemaDeclaration),
        read('synthetic_generation_request_20261018.json', GenerationRequest),
        read(f'synthetic_reuse_{kind}_table_20261019.json', AlternateSyntheticTable),
        read(f'synthetic_reuse_{kind}_cases_20261019.json', SchemaAcceptanceCases),
        read(f'synthetic_reuse_{kind}_query_cases_20261019.json', QueryPlan),
    )


@pytest.fixture(scope='module')
def base_preview():
    with tempfile.TemporaryDirectory(prefix='astra-synth-base-') as d:
        root = Path(d)
        ob, schema, request, table, cases, plan = inputs()
        run_schema_reuse(ob, F, schema, request, table, cases, root)
        yield root


@pytest.fixture
def preview(base_preview):
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as d:
        root = Path(d)
        shutil.copytree(base_preview, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.sqlite3'))
        yield root


def _run_embedded(root: Path, script: str):
    cmd = [sys.executable, '-c', script]
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=15)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout.strip()


def test_product_app_end_to_end_in_same_generated_project(preview):
    ob, schema, request, table, cases, plan = inputs()
    before = {p: (preview / p).read_bytes() for p in ['app/main.py', 'app/index.html', 'data/seed.json']}
    out = embed_in_preview(table, plan, preview)
    assert out.status == 'generated_synthetic_query_integrated_passed'
    assert out.accepted_cases == 9 and out.generated_entrypoint == 'app.extended:app'
    assert out.original_app_source_unchanged
    assert not out.original_site_behavior_verified
    assert not out.customer_database_accessed
    assert not out.code_generation_authorized and not out.deployment_authorized
    for key, value in before.items():
        assert (preview / key).read_bytes() == value
    assert (preview / 'app/extended.py').read_text() == _added_files(table, plan)['app/extended.py']
    assert (preview / 'data/query_embed_report.json').is_file()
    assert (preview / 'tests/test_embedded_query.py').read_text() == GENERATED_TEST
    result = _run_embedded(preview, 'from app.extended import app\nfrom fastapi.testclient import TestClient\nwith TestClient(app) as c:\n print(c.get("/api/rows", params={"sort_by":"popularity","direction":"desc"}).json()["items"][0]["sku"])')
    assert result == 'prod-shimmer'


def test_ticket_app_entire_generation_workflow(tmp_path):
    ob, schema, req, table, acceptance, plan = inputs('tickets')
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root=Path(folder)
        old=fingerprint(ob)
        report=generate_integrated_preview(ob,F,schema,req,table,acceptance,plan,root)
        assert report.accepted_cases==9
        assert fingerprint(ob)==old
        assert (root/'app/main.py').read_text()==APP
        assert (root/'app/index.html').read_text()==HTML
        assert (root/'data/schema_reuse_report.json').is_file()
        assert (root/'data/query_embed_report.json').is_file()
        response=_run_embedded(root, 'from app.extended import app\nfrom fastapi.testclient import TestClient\nwith TestClient(app) as c:\n print(c.get("/api/rows",params={"sort_by":"priority","direction":"desc"}).status_code, c.get("/health").status_code)')
        assert response=='200 200'


def test_wrong_query_sha_fails_before_writes():
    ob,schema,req,table,acc,plan=inputs()
    bad=plan.model_copy(update={'source_table_sha256':'0'*64})
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as d:
        with pytest.raises(ValueError,match='stale'):
            generate_integrated_preview(ob,F,schema,req,table,acc,bad,Path(d))
        assert list(Path(d).iterdir())==[]


def test_wrong_expected_ids_fail_before_writes():
    ob,schema,req,table,acc,plan=inputs()
    data=plan.model_dump(mode='json')
    data['cases'][0]['expected_ids']=['wrong-id']
    bad=QueryPlan.model_validate(data)
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as d:
        with pytest.raises(ValueError,match='mismatched'):
            generate_integrated_preview(ob,F,schema,req,table,acc,bad,Path(d))
        assert list(Path(d).iterdir())==[]


def test_wrong_base_template_rejected(preview):
    _,_,_,table,_,plan=inputs()
    (preview/'app/main.py').write_text('print("corrupt")')
    with pytest.raises(ValueError,match='template'):
        embed_in_preview(table,plan,preview)
    assert not (preview/'app/extended.py').exists()


def test_wrong_html_rejected(preview):
    _,_,_,table,_,plan=inputs()
    (preview/'app/index.html').write_text('<html>wrong</html>')
    with pytest.raises(ValueError,match='template'):
        embed_in_preview(table,plan,preview)
    assert not (preview/'app/extended.py').exists()


def test_missing_trace_rejected(preview):
    _,_,_,table,_,plan=inputs()
    (preview/'data/astra_preview_trace.json').unlink()
    with pytest.raises(ValueError,match='required preview file'):
        embed_in_preview(table,plan,preview)


def test_symlinked_preview_folder_rejected(preview):
    _,_,_,table,_,plan=inputs()
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as d:
        link=Path(d)/'fake'
        link.symlink_to(preview, target_is_directory=True)
        with pytest.raises(ValueError,match='isolated'):
            embed_in_preview(table,plan,link)


def test_non_temporary_output_rejected(tmp_path):
    _,_,_,table,_,plan=inputs()
    with pytest.raises(ValueError,match='isolated'):
        embed_in_preview(table,plan,tmp_path)


def test_preexisting_output_not_overwritten(preview):
    _,_,_,table,_,plan=inputs()
    path=preview/'app/extended.py'
    path.write_text('PRESERVE')
    with pytest.raises(ValueError,match='overwrite'):
        embed_in_preview(table,plan,preview)
    assert path.read_text()=='PRESERVE'


def test_existing_report_not_overwritten(preview):
    _,_,_,table,_,plan=inputs()
    path=preview/'data/query_embed_report.json'
    path.write_text('PRESERVE')
    with pytest.raises(ValueError,match='overwrite'):
        embed_in_preview(table,plan,preview)
    assert path.read_text()=='PRESERVE'


def test_existing_symlink_output_not_followed(preview, tmp_path):
    _,_,_,table,_,plan=inputs()
    outside=tmp_path/'victim.txt';outside.write_text('PRESERVE')
    (preview/'app/extended.py').symlink_to(outside)
    with pytest.raises(ValueError,match='overwrite'):
        embed_in_preview(table,plan,preview)
    assert outside.read_text()=='PRESERVE'


def test_generated_runtime_blocks_tampered_fixture(preview):
    _,_,_,table,_,plan=inputs()
    embed_in_preview(table,plan,preview)
    path=preview/'data/query_physical_fixture.json'
    path.write_text(path.read_text(encoding='utf-8')+' ')
    output=_run_embedded(preview, 'try:\n from app.extended import app\nexcept ValueError as exc:\n assert "changed" in str(exc)\n print("BLOCKED")\nelse: raise RuntimeError("must reject")')
    assert output=='BLOCKED'


def test_generated_runtime_blocks_symlink_fixture(preview,tmp_path):
    _,_,_,table,_,plan=inputs()
    embed_in_preview(table,plan,preview)
    p=preview/'data/query_physical_fixture.json'
    outside=tmp_path/'external.json'
    outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside)
    output=_run_embedded(preview,'try:\n from app.extended import app\nexcept ValueError as exc:\n assert "symlinked" in str(exc)\n print("BLOCKED")\nelse: raise RuntimeError("must reject")')
    assert output=='BLOCKED'


def test_post_generated_api_strict_query_422(preview):
    _,_,_,table,_,plan=inputs()
    embed_in_preview(table,plan,preview)
    output=_run_embedded(preview, '''from app.extended import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
 assert c.get("/api/rows",params={"sort_by":"sku","filter_by":"popularity","filter_value":"-1"}).status_code==422
 assert c.get("/api/rows",params={"sort_by":"sku","filter_by":"popularity","filter_value":"01"}).status_code==422
 assert c.get("/api/rows",params={"sort_by":"sku","filter_by":"popularity","filter_value":"1 OR 1=1"}).status_code==422
 assert c.get("/api/rows",params={"sort_by":"sku","direction":"DROP TABLE"}).status_code==422
 assert c.get("/api/rows",params={"sort_by":"sku","filter_by":"family","filter_value":"Colors"}).json()["items"]==[]
 print("STRICT")''')
    assert output=='STRICT'


def test_fake_permission_rejected_by_fixture(preview):
    _,_,_,table,_,plan=inputs()
    x=table.model_dump(mode='json');x['schema_mapping_approved']=True
    with pytest.raises(ValidationError):
        embed_in_preview(AlternateSyntheticTable.model_validate(x),plan,preview)
    assert not (preview/'app/extended.py').exists()


def test_fake_permission_rejected_by_plan(preview):
    _,_,_,table,_,plan=inputs()
    x=plan.model_dump(mode='json');x['deployment_authorized']=True
    with pytest.raises(ValidationError):
        embed_in_preview(table,QueryPlan.model_validate(x),preview)
    assert not (preview/'app/extended.py').exists()


def test_mismatched_other_table_query_contract(preview):
    _,_,_,table,_,_=inputs()
    _,_,_,_,_,plan=inputs('tickets')
    with pytest.raises(ValueError,match='stale'):
        embed_in_preview(table,plan,preview)
    assert not (preview/'app/extended.py').exists()


def test_safe_template_contains_no_operator_dynamic_code():
    _,_,_,table,_,plan=inputs()
    data=_added_files(table,plan)
    assert 'import astra_contracts' not in data['app/extended.py']
    assert 'eval(' not in data['app/extended.py']
    assert 'exec(' not in data['app/extended.py']
    assert '__FIXTURE_SHA256__' not in data['app/extended.py']
    assert 'from app.main import create_app' in data['app/extended.py']
    assert '/api/rows' in data['app/extended.py']
    assert 'CREATE TABLE' not in data['app/extended.py']


def test_output_report_false_literal_cannot_be_forged():
    d=EmbeddedQueryReport(physical_table_sha256='1'*64,query_cases_sha256='2'*64,
                          base_preview_sha256='3'*64,accepted_cases=9).model_dump(mode='json')
    for name in ('original_site_behavior_verified','customer_database_accessed',
                 'code_generation_authorized','deployment_authorized'):
        modified=dict(d);modified[name]=True
        with pytest.raises(ValidationError):
            EmbeddedQueryReport.model_validate(modified)


def test_invalid_physical_column_rejected_in_preflight():
    _,_,_,table,_,plan=inputs()
    d=plan.model_dump(mode='json');d['cases'][0]['sort_by']='malicious_column'
    with pytest.raises(ValueError,match='query API returned'):
        verify_query_plan(table,QueryPlan.model_validate(d))


def test_cli_synthetic_product_pipeline(tmp_path,capsys):
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        args=[str(F/'synthetic_manual_filter_observation_20261019.json'),str(F),
              str(F/'synthetic_manual_filter_schema_20261019.json'),
              str(F/'synthetic_generation_request_20261018.json'),
              str(F/'synthetic_reuse_products_table_20261019.json'),
              str(F/'synthetic_reuse_products_cases_20261019.json'),
              str(F/'synthetic_reuse_products_query_cases_20261019.json'),folder]
        assert main(args)==0
        data=json.loads(capsys.readouterr().out)
        assert data['accepted_cases']==9
        assert data['generated_entrypoint']=='app.extended:app'
        assert data['code_generation_authorized'] is False


def test_read_only_route_has_no_post_put_delete(preview):
    _,_,_,table,_,plan=inputs()
    embed_in_preview(table,plan,preview)
    output=_run_embedded(preview, '''from app.extended import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
 for method in ("post","put","patch","delete"):
  assert getattr(c,method)("/api/rows").status_code==405
 print("READONLY")''')
    assert output=='READONLY'


def test_script_from_other_environment_is_blocked(preview):
    _,_,_,table,_,plan=inputs()
    embed_in_preview(table,plan,preview)
    bad=(preview/'data/query_cases.json')
    bad.write_text('{}')
    # Runtime uses only validated, SHA-bound fixture. A test-contract mutation
    # cannot change returned data; human expectations are not used by the server.
    output=_run_embedded(preview,'''from app.extended import app
from fastapi.testclient import TestClient
with TestClient(app) as c:
 assert c.get("/api/rows",params={"sort_by":"sku"}).status_code==200
 print("ISOLATED")''')
    assert output=='ISOLATED'
