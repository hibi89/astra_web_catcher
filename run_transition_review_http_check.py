"""Build and exercise a local, fictional-only transition review preview; no browser."""
from __future__ import annotations
import json, os, socket, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
import httpx

from astra_contracts.capture_intake import CaptureIntakeRequest, register_captures
from astra_contracts.capture_transition_ledger import TransitionPlan
from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_crud_embed import embed_synthetic_crud
from astra_contracts.schema_query_embed import generate_integrated_preview
from astra_contracts.schema_query_extension import QueryPlan
from astra_contracts.schema_query_ui import embed_query_ui
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, SchemaAcceptanceCases
from astra_contracts.mapping_review_ui import embed_review_ui
from astra_contracts.observed_ui_mapping import UIActionMappingPlan, UIActionMappingReport
from astra_contracts.transition_review_ui import embed_transition_review_ui

BASE=Path(__file__).resolve().parent
FIX=BASE/'fixtures'
OUT=Path('/mnt/data')
def read(filename, model): return model.model_validate_json((FIX/filename).read_bytes())
def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

def build(kind,root,intake):
    generate_integrated_preview(
        read('synthetic_manual_filter_observation_20261019.json',ObservationBundle),FIX,
        read('synthetic_manual_filter_schema_20261019.json',OwnedSchemaDeclaration),
        read('synthetic_generation_request_20261018.json',GenerationRequest),
        read(f'synthetic_reuse_{kind}_table_20261019.json',AlternateSyntheticTable),
        read(f'synthetic_reuse_{kind}_cases_20261019.json',SchemaAcceptanceCases),
        read(f'synthetic_reuse_{kind}_query_cases_20261019.json',QueryPlan),root)
    embed_synthetic_crud(root)
    embed_query_ui(root)
    stem=f'synthetic_ui_mapping_{kind}_20261019'
    embed_review_ui(root,
        read(stem+'_observation.json',ObservationBundle),
        read(stem+'_schema.json',OwnedSchemaDeclaration),
        read(f'synthetic_reuse_{kind}_table_20261019.json',AlternateSyntheticTable),
        read(stem+'_plan.json',UIActionMappingPlan),FIX,
        read('synthetic_ui_mapping_archive_report_20261019.json',UIActionMappingReport))
    return embed_transition_review_ui(root,
        read('synthetic_transition_pair_observation_20261019.json',ObservationBundle),intake,
        read('synthetic_transition_pair_plan_20261019.json',TransitionPlan))

def smoke(root,kind):
    port=free_port();base=f'http://127.0.0.1:{port}'
    env=dict(os.environ);env.pop('ASTRA_ENABLE_SYNTHETIC_CRUD',None)
    app=subprocess.Popen([sys.executable,'-m','uvicorn','app.transitions:app','--host','127.0.0.1','--port',str(port),'--log-level','error'],
        cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for i in range(80):
            if app.poll() is not None: raise RuntimeError('server quit '+app.communicate()[1].decode()[-700:])
            try:
                if httpx.get(base+'/health',timeout=.5).status_code==200:break
            except (httpx.ConnectError,httpx.ReadTimeout):time.sleep(.12)
        else:raise RuntimeError('timeout waiting for localhost server')
        with httpx.Client(base_url=base,timeout=7) as client:
            status={}
            for path in ['/','/health','/preview','/preview-mapped','/preview-transitions',
                         '/api/review-manifest','/api/transition-ledger','/api/preview-schema']:
                rsp=client.get(path);assert rsp.status_code==200,(path,rsp.status_code,rsp.text[:120]);status[path]=rsp.status_code
            content=client.get('/preview-transitions').text
            assert 'id="transition-review"' in content and 'id="mapping-review"' in content
            manifest=client.get('/api/transition-ledger').json()
            assert len(manifest['findings'])==1
            assert manifest['findings'][0]['status']=='paired_bytes_present_unverified'
            assert manifest['findings'][0]['enabled'] is False
            assert manifest['original_site_behavior_verified'] is False
            assert manifest['capture_files_rechecked_at_request'] is False
            assert client.post('/api/items',json={}).status_code==405
            assert client.get('/sandbox/api/items').status_code==404
            query={'sort_by':'family','filter_by':'family','filter_value':'colors'} if kind=='products' else {'sort_by':'lane','filter_by':'lane','filter_value':'Open'}
            data=client.get('/api/rows',params=query)
            assert data.status_code==200
            assert len(data.json()['items'])==(2 if kind=='products' else 3)
            return {'kind':kind,'all_routes':status,'transition_status':manifest['findings'][0]['status'],
                    'filter_count':len(data.json()['items']),'original_POST':405,'sandbox_get':404,
                    'original_site_verified':False,'real_browser_verified':False,'owner_db_connected':False}
    finally:
        app.terminate()
        try:app.communicate(timeout=5)
        except subprocess.TimeoutExpired:app.kill();app.communicate()


def run():
    with tempfile.TemporaryDirectory(prefix='astra-capture-') as intake_temp:
        intake=Path(intake_temp)
        register_captures(read('synthetic_transition_pair_observation_20261019.json',ObservationBundle),FIX,
                          read('synthetic_transition_pair_intake_request_20261019.json',CaptureIntakeRequest),intake)
        results=[]
        for kind in ['products','tickets']:
            with tempfile.TemporaryDirectory(prefix='astra-synth-') as temp:
                root=Path(temp)
                report=build(kind,root,intake)
                outcome=smoke(root,kind)
                outcome['generated_status']=report.status
                results.append(outcome)
                if kind=='products':
                    path=OUT/'astra_p4_transition_review_generated_preview_20261019.zip'
                    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as zipout:
                        for asset in root.rglob('*'):
                            if (asset.is_file() and not any(x in asset.parts for x in ['__pycache__','.pytest_cache'])
                                    and asset.suffix not in ['.sqlite3','.pyc']):
                                zipout.write(asset,asset.relative_to(root))
        summary={'project':'p4','name':'generated transition provenance review','fixtures_only':True,
                 'actual_browser_visual_verified':False,'actual_reference_site_verified':False,
                 'owner_database_connected':False,'customer_authorization':False,
                 'results':results}
        path=OUT/'astra_p4_transition_review_http_verification_20261019.json'
        path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
