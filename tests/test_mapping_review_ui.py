"""Offline trace candidate -> DISABLED synthetic-app UI, never approval."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest
from astra_contracts.observation import ObservationBundle
from astra_contracts.observed_ui_mapping import (
    UIActionMappingPlan, UIActionMappingReport, build_ui_mapping,
)
from astra_contracts.mapping_review_ui import (
    ReviewManifest, REVIEW_HTML, build_review_manifest, embed_review_ui,
)
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, SchemaAcceptanceCases
from astra_contracts.schema_query_embed import generate_integrated_preview
from astra_contracts.schema_query_extension import QueryPlan
from astra_contracts.schema_crud_embed import embed_synthetic_crud
from astra_contracts.schema_query_ui import embed_query_ui

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'fixtures'


def load(name, cls):
    return cls.model_validate_json((F / name).read_bytes())


def inputs(kind):
    stem=f'synthetic_ui_mapping_{kind}_20261019'
    bundle=load(stem+'_observation.json', ObservationBundle)
    declaration=load(stem+'_schema.json', OwnedSchemaDeclaration)
    table=load(f'synthetic_reuse_{kind}_table_20261019.json', AlternateSyntheticTable)
    plan=load(stem+'_plan.json',UIActionMappingPlan)
    return bundle,declaration,table,plan


def blocked_report():
    return load('synthetic_ui_mapping_archive_report_20261019.json',UIActionMappingReport)


@pytest.mark.parametrize('kind,field,value', [('products','family','colors'),('tickets','lane','Open')])
def test_review_manifest_never_enables_a_candidate(kind,field,value):
    b,d,t,p=inputs(kind)
    review=build_review_manifest(build_ui_mapping(b,d,t,p,F),t,blocked_report())
    assert review.mapping_actions_enabled is False
    assert review.owner_database_access_authorized is False
    assert review.original_site_behavior_verified is False
    assert len(review.items)==2
    candidate, archive=review.items
    assert candidate.enabled is False and candidate.proposed_filter_by==field
    assert candidate.proposed_filter_value==value
    assert candidate.status=='synthetic_preview_candidate_unapproved'
    assert archive.enabled is False and archive.status=='archived_secondary_only'
    assert archive.proposed_filter_by is None and archive.proposed_filter_value is None
    assert 'innerHTML' not in REVIEW_HTML
    assert 'button.disabled=true' in REVIEW_HTML
    assert 'textContent' in REVIEW_HTML


def test_wrong_table_fails_closed():
    b,d,t,p=inputs('products')
    report=build_ui_mapping(b,d,t,p,F)
    other=inputs('tickets')[2]
    with pytest.raises(ValueError,match='does not match'):
        build_review_manifest(report,other)


def test_blocked_report_cannot_be_promoted():
    b,d,t,p=inputs('products')
    report=build_ui_mapping(b,d,t,p,F)
    with pytest.raises(ValueError,match='no candidates'):
        build_review_manifest(report,t,report)


def test_forged_review_approval_flags_fail_validation():
    b,d,t,p=inputs('products')
    raw=build_review_manifest(build_ui_mapping(b,d,t,p,F),t).model_dump()
    for obj in ('mapping_actions_enabled','owner_database_access_authorized','generation_authorized'):
        copyraw=copy.deepcopy(raw)
        copyraw[obj]=True
        with pytest.raises(ValidationError):
            ReviewManifest.model_validate(copyraw)
    copyraw=copy.deepcopy(raw)
    copyraw['items'][0]['enabled']=True
    with pytest.raises(ValidationError):
        ReviewManifest.model_validate(copyraw)


@pytest.fixture(scope='module',params=['products','tickets'])
def generated_base(request):
    kind=request.param
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as temp:
        root=Path(temp)
        generate_integrated_preview(
            load('synthetic_manual_filter_observation_20261019.json',ObservationBundle),F,
            load('synthetic_manual_filter_schema_20261019.json',OwnedSchemaDeclaration),
            load('synthetic_generation_request_20261018.json',GenerationRequest),
            load(f'synthetic_reuse_{kind}_table_20261019.json',AlternateSyntheticTable),
            load(f'synthetic_reuse_{kind}_cases_20261019.json',SchemaAcceptanceCases),
            load(f'synthetic_reuse_{kind}_query_cases_20261019.json',QueryPlan),root)
        embed_synthetic_crud(root)
        embed_query_ui(root)
        yield kind,root


@pytest.fixture
def cloned(generated_base):
    kind,original=generated_base
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as temp:
        root=Path(temp)
        shutil.copytree(original,root,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3'))
        yield kind,root


def attach(kind,root,blocked=True):
    b,d,t,p=inputs(kind)
    return embed_review_ui(root,b,d,t,p,F,blocked_report() if blocked else None)


def invoke(root, code):
    result=subprocess.run([sys.executable,'-c',code],cwd=root,text=True,capture_output=True,timeout=20)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    return result.stdout


def test_generated_ui_review_panel_all_disabled(cloned):
    kind,root=cloned
    originals={p:(root/p).read_bytes() for p in
               ['app/main.py','app/index.html','app/ui.py','app/query_ui.html','app/full.py','data/seed.json']}
    report=attach(kind,root)
    assert report.mapping_actions_enabled is False
    assert report.generated_entrypoint=='app.mapped:app'
    assert report.customer_database_connected is False
    for p,body in originals.items():
        assert (root/p).read_bytes()==body
    assert (root/'app/mapped_review.html').read_text(encoding='utf-8')==REVIEW_HTML
    out=invoke(root,'''from fastapi.testclient import TestClient
from app.mapped import create_mapped_app
with TestClient(create_mapped_app()) as c:
 assert c.get('/preview-mapped').status_code==200
 html=c.get('/preview-mapped').text
 assert 'id="mapping-review"' in html and 'button.disabled=true' in html
 manifest=c.get('/api/review-manifest').json()
 assert len(manifest['items'])==2
 assert all(x['enabled'] is False for x in manifest['items'])
 assert manifest['items'][1]['status']=='archived_secondary_only'
 assert c.get('/preview').status_code==200
 assert c.get('/api/rows',params={'sort_by':manifest['items'][0]['proposed_filter_by']}).status_code==200
 assert c.get('/sandbox/api/items').status_code==404
 assert c.post('/api/items',json={}).status_code==405
print('MAPPING_UI_DISABLED_PASS')''')
    assert 'MAPPING_UI_DISABLED_PASS' in out


def test_cannot_overwrite_existing_mapped_page(cloned):
    kind,root=cloned
    (root/'app/mapped_review.html').write_text('PRESERVE',encoding='utf-8')
    with pytest.raises(ValueError,match='overwrite'):
        attach(kind,root)
    assert (root/'app/mapped_review.html').read_text()=='PRESERVE'
    assert not (root/'app/mapped.py').exists()


def test_reject_prior_ui_tampering(cloned):
    kind,root=cloned
    (root/'app/query_ui.html').write_text('<script>bad()</script>')
    with pytest.raises(ValueError,match='tampered'):
        attach(kind,root)
    assert not (root/'app/mapped.py').exists()


def test_reject_forged_evidence_and_missing_original(cloned):
    kind,root=cloned
    b,d,t,p=inputs(kind)
    raw=p.model_dump(mode='json')
    raw['evidence_sha256_by_id'][next(iter(raw['evidence_sha256_by_id']))]='0'*64
    with pytest.raises(ValueError,match='evidence integrity'):
        embed_review_ui(root,b,d,t,UIActionMappingPlan.model_validate(raw),F)
    assert not (root/'app/mapped.py').exists()


def test_runtime_tamper_manifest_is_503(cloned):
    kind,root=cloned
    attach(kind,root)
    file=root/'data/review_manifest.json'
    data=json.loads(file.read_text())
    data['items'][0]['enabled']=True
    file.write_text(json.dumps(data),encoding='utf-8')
    invoke(root,'''from app.mapped import create_mapped_app
from fastapi.testclient import TestClient
with TestClient(create_mapped_app()) as c:
 assert c.get('/api/review-manifest').status_code==503
 assert c.get('/preview-mapped').status_code==503
print('TAMPER_BLOCKED')''')


def test_runtime_tamper_mapped_html_is_503(cloned):
    kind,root=cloned
    attach(kind,root)
    (root/'app/mapped_review.html').write_text('<script>bad()</script>')
    invoke(root,'''from app.mapped import create_mapped_app
from fastapi.testclient import TestClient
with TestClient(create_mapped_app()) as c:
 assert c.get('/api/review-manifest').status_code==503
 assert c.get('/preview-mapped').status_code==503
print('TAMPER_BLOCKED')''')


def test_root_not_arbitrary(tmp_path):
    b,d,t,p=inputs('products')
    with pytest.raises(ValueError,match='isolated'):
        embed_review_ui(tmp_path,b,d,t,p,F)


def test_mapping_review_rejects_opt_in_crud_mode(cloned):
    kind,root=cloned
    attach(kind,root)
    import os
    env=dict(os.environ,ASTRA_ENABLE_SYNTHETIC_CRUD='YES_TEMP_ONLY')
    p=subprocess.run([sys.executable,'-c','import app.mapped'],cwd=root,
                     env=env,capture_output=True,text=True,timeout=20)
    assert p.returncode!=0
    assert 'cannot launch with write-enabled' in p.stderr
