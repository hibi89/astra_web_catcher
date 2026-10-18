"""Add a usable, fixed *fictional-data-only* sort/filter page to a verified preview.

This never edits the protected original generated UI, original site, owner data,
CRUD permissions, or production deployment. A separate localhost-only entrypoint
serves /preview and the existing optional synthetic CRUD /sandbox routes.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from astra_contracts.schema_crud_embed import (
    CRUD_SOURCE, FULL_SOURCE, CRUDEmbedReport, _preview_guards,
)
from astra_contracts.schema_query_embed import _safe_root
from astra_contracts.generation_contract import fingerprint
from astra_contracts.synthetic_generator import APP, HTML

QUERY_UI_HTML = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASTRA · 합성 데이터 미리보기</title>
<style>
:root{font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif;color:#16263b;background:#f4f7fc;color-scheme:light}
*{box-sizing:border-box}body{margin:0}.wrap{max-width:1100px;margin:0 auto;padding:36px 24px 68px}
.eyebrow{font-size:12px;font-weight:750;letter-spacing:.1em;color:#385dc6;text-transform:uppercase}
h1{font-size:32px;line-height:1.2;margin:11px 0 10px}p{line-height:1.6}.muted{color:#58677a}
.notice{background:#e8efff;color:#234782;padding:12px 16px;border:1px solid #c1d2ff;border-radius:10px;margin:20px 0}
.panel{background:#fff;border:1px solid #dce4f1;border-radius:16px;padding:24px;box-shadow:0 10px 30px #10254c0b;margin-top:18px}
.controls{display:grid;grid-template-columns:1.5fr 1fr 1.5fr 1fr;gap:13px}
label{display:flex;flex-direction:column;gap:7px;font-size:13px;font-weight:650}
select,input{min-width:0;width:100%;border:1px solid #cbd6e6;background:white;border-radius:8px;padding:11px;font-size:14px;color:#172b46}
select:focus-visible,input:focus-visible,button:focus-visible{outline:3px solid #7494ff;outline-offset:2px}
.actions{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:20px}
button{background:#315bd0;border:0;color:white;font-size:14px;font-weight:700;padding:12px 20px;border-radius:9px;cursor:pointer}
button:disabled{background:#8b9dbb;cursor:not-allowed}#feedback{min-height:24px;font-size:13px}#feedback[role=alert]{color:#a62424}
.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;min-width:650px;font-size:14px}
th{text-align:left;background:#f4f7fd;font-weight:700;color:#425576;padding:13px;border-bottom:1px solid #dce4f1}
td{padding:15px 13px;border-bottom:1px solid #e7ebf2}tbody tr:hover{background:#f8faff}
@media(max-width:780px){.controls{grid-template-columns:1fr 1fr}.wrap{padding:24px 15px}h1{font-size:26px}}
@media(max-width:450px){.controls{grid-template-columns:1fr}}
</style></head>
<body><main class="wrap"><div class="eyebrow">ASTRA / EXPERIMENTAL PREVIEW</div>
<h1>데이터 정렬 · 필터 미리보기</h1>
<p class="muted">선언된 데이터 필드만 선택해 결과를 살펴볼 수 있습니다.</p>
<div class="notice"><strong>가상 데이터 전용</strong> · 원본 사이트 동작을 검증한 화면이 아니며, 고객 DB에 연결되지 않습니다.</div>
<section class="panel" aria-labelledby="config-heading"><h2 id="config-heading">조회 조건</h2>
<p id="dataset" class="muted">가상 데이터 형식을 읽는 중…</p>
<form id="query-form"><div class="controls">
<label for="sort-field">정렬 필드<select id="sort-field" name="sort-field" required disabled></select></label>
<label for="sort-direction">정렬 방향<select id="sort-direction" name="sort-direction" disabled><option value="asc">오름차순</option><option value="desc">내림차순</option></select></label>
<label for="filter-field">필터 필드<select id="filter-field" name="filter-field" disabled><option value="">필터 없음</option></select></label>
<label for="filter-value">일치하는 값<input id="filter-value" name="filter-value" type="text" placeholder="필터를 선택하세요" disabled></label>
</div><div class="actions"><span id="feedback" aria-live="polite">필드를 불러오는 중입니다.</span><button id="apply" type="submit" disabled>결과 조회</button></div></form></section>
<section class="panel" aria-labelledby="result-heading"><h2 id="result-heading">조회 결과</h2>
<div class="table-wrap"><table><thead><tr id="columns"></tr></thead><tbody id="results"></tbody></table></div>
</section></main>
<script>
'use strict';
const $ = id => document.getElementById(id);
let schema = null;
let requestSerial = 0;
function addOption(select, value, caption) {
  const option = document.createElement('option'); option.value=value; option.textContent=caption; select.appendChild(option);
}
function fail(message) {
  const feedback=$('feedback'); feedback.setAttribute('role','alert'); feedback.textContent=message;
}
function setFilterMode() {
  const selected=$('filter-field').value;
  const field=schema?.fields.find(x => x.name === selected);
  const input=$('filter-value'); input.disabled=!field; input.value='';
  input.type=field?.type==='integer'?'number':'text';
  if (field?.type==='integer') {input.min='0';input.max='10000';input.step='1';}
  else {input.removeAttribute('min');input.removeAttribute('max');input.removeAttribute('step');}
  input.placeholder=field? (field.type==='integer'?'0~10000 정수':'일치할 문자열') :'필터를 선택하세요';
}
async function render() {
  if (!schema) return;
  const sortField=$('sort-field').value, filterField=$('filter-field').value;
  if (!schema.fields.some(x => x.name===sortField)) {fail('선언되지 않은 정렬 필드입니다.');return;}
  if (filterField && !schema.fields.some(x => x.name===filterField)) {fail('선언되지 않은 필터 필드입니다.');return;}
  if (filterField && $('filter-value').value==='') {fail('필터 값을 입력하세요.');return;}
  const params = new URLSearchParams({sort_by:sortField,direction:$('sort-direction').value,limit:'100'});
  if (filterField) {params.set('filter_by',filterField); params.set('filter_value',$('filter-value').value);}
  const serial=++requestSerial; $('apply').disabled=true; $('feedback').removeAttribute('role'); $('feedback').textContent='조회 중…';
  try {
    const response=await fetch('/api/rows?'+params.toString(),{cache:'no-store'});
    if (!response.ok) throw new Error('조회 실패 (HTTP '+response.status+')');
    const data=await response.json();
    if (!data.synthetic || data.original_site_behavior_verified!==false || !Array.isArray(data.items)) throw new Error('합성 데이터 계약이 올바르지 않습니다.');
    if (serial!==requestSerial) return;
    const columns=$('columns'); columns.replaceChildren();
    for (const field of schema.fields) {const th=document.createElement('th');th.textContent=field.name;th.scope='col';columns.appendChild(th);}
    const body=$('results');body.replaceChildren();
    for (const item of data.items) {
      const tr=document.createElement('tr');
      for (const field of schema.fields) {const td=document.createElement('td');td.textContent=String(item[field.name] ?? '');tr.appendChild(td);}
      body.appendChild(tr);
    }
    $('feedback').textContent=data.items.length+'개 결과 · 가상 데이터';
  } catch(e) {if (serial===requestSerial) fail(e.message);}
  finally {if (serial===requestSerial) $('apply').disabled=false;}
}
async function boot() {
  try {
    const response=await fetch('/api/preview-schema',{cache:'no-store'});
    if (!response.ok) throw new Error('필드 정보를 읽을 수 없습니다.');
    const value=await response.json();
    if (!value.synthetic || value.original_site_behavior_verified!==false || !Array.isArray(value.fields) || value.fields.length!==4) throw new Error('잘못된 합성 스키마입니다.');
    schema=value;
    $('dataset').textContent='가상 테이블: '+schema.table_name;
    for (const field of schema.fields) {addOption($('sort-field'),field.name,field.name);addOption($('filter-field'),field.name,field.name+' ('+(field.type==='integer'?'정수':'문자열')+')');}
    $('sort-field').disabled=false;$('sort-direction').disabled=false;$('filter-field').disabled=false;$('apply').disabled=false;
    $('filter-field').addEventListener('change',setFilterMode);
    $('query-form').addEventListener('submit',event=>{event.preventDefault();render();});
    await render();
  } catch(e) {fail(e.message);}
}
boot();
</script></body></html>
'''

UI_SOURCE = '''"""Optional synthetic-only GUI; never modifies the fixed generated demo."""
import hashlib
import json
import os
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.full import create_full_app
from app.extended import FIXTURE_SHA256

ROOT = Path(__file__).resolve().parents[1]
UI_SHA256 = "__UI_SHA256__"


def create_ui_app(base_db_path=None, *, enable_synthetic_crud=False):
    app=create_full_app(base_db_path, enable_synthetic_crud=enable_synthetic_crud)
    html_path=ROOT/'app'/'query_ui.html'
    physical_path=ROOT/'data'/'query_physical_fixture.json'

    def checked_html():
        if html_path.is_symlink() or not html_path.is_file():
            raise HTTPException(503,'synthetic UI unavailable')
        if hashlib.sha256(html_path.read_bytes()).hexdigest()!=UI_SHA256:
            raise HTTPException(503,'synthetic UI integrity check failed')
        return html_path

    @app.get('/preview',include_in_schema=False)
    def query_preview():
        return FileResponse(checked_html(), media_type='text/html',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/api/preview-schema',include_in_schema=False)
    def preview_schema():
        checked_html()
        if physical_path.is_symlink() or not physical_path.is_file():
            raise HTTPException(503,'synthetic fields missing')
        payload=physical_path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=FIXTURE_SHA256:
            raise HTTPException(503,'synthetic field fixture integrity failure')
        table=json.loads(payload)
        if (table.get('source_kind')!='synthetic_fixture' or table.get('run_mode')!='temporary_demo_only'
                or table.get('customer_database_connected') is not False
                or table.get('original_site_behavior_verified') is not False):
            raise HTTPException(503,'synthetic-only markers missing')
        if len(table['bindings'])!=4 or set(x['logical_field'] for x in table['bindings'])!={'id','title','category','score'}:
            raise HTTPException(503,'unrecognized declared fields')
        declared=[{'name':x['source_field'],'type':'integer' if x['logical_field']=='score' else 'text'}
                  for x in table['bindings']]
        return JSONResponse({'synthetic':True,'original_site_behavior_verified':False,
                             'table_name':table['table_name'],'fields':declared},
                             headers={'Cache-Control':'no-store'})
    return app


app=create_ui_app(enable_synthetic_crud=(os.environ.get('ASTRA_ENABLE_SYNTHETIC_CRUD')=='YES_TEMP_ONLY'))
'''

GENERATED_TEST = '''"""Generated UI is bound to explicitly declared synthetic fields."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.ui import create_ui_app

ROOT=Path(__file__).resolve().parents[1]


def test_readonly_ui_controls_and_schema(tmp_path):
    app=create_ui_app(tmp_path/'local_demo.sqlite3')
    with TestClient(app) as c:
        response=c.get('/preview')
        assert response.status_code==200
        assert '가상 데이터 전용' in response.text
        assert 'id="filter-field"' in response.text
        assert 'id="sort-field"' in response.text
        assert c.get('/').status_code==200
        assert c.post('/api/items',json={}).status_code==405
        assert c.get('/sandbox/api/items').status_code==404
        manifest=c.get('/api/preview-schema')
        assert manifest.status_code==200
        m=manifest.json()
        assert m['synthetic'] and m['original_site_behavior_verified'] is False
        fixture=json.loads((ROOT/'data/query_physical_fixture.json').read_text(encoding='utf-8'))
        assert [x['name'] for x in m['fields']]==[b['source_field'] for b in fixture['bindings']]
        query_cases=json.loads((ROOT/'data/query_cases.json').read_text(encoding='utf-8'))
        key=next(b['source_field'] for b in fixture['bindings'] if b['logical_field']=='id')
        for case in query_cases['cases']:
            params={k:case[k] for k in ('sort_by','direction','limit')}
            if case['filter_by'] is not None:
                params.update(filter_by=case['filter_by'],filter_value=case['filter_value'])
            result=c.get('/api/rows',params=params)
            assert result.status_code==200
            assert [r[key] for r in result.json()['items']]==case['expected_ids']
        assert c.get('/api/rows',params={'sort_by':'__proto__'}).status_code==422
'''

README = '''# ASTRA fictional preview with human-sortable/queryable UI

Start on **localhost only**:

```sh
python -m uvicorn app.ui:app --host 127.0.0.1 --port 8017
```

Open `http://127.0.0.1:8017/preview` to sort, choose a declared exact-match
string/integer filter, and render results from read-only `/api/rows`. The UI
loads its synthetic field names from `/api/preview-schema`. The original `/`
route, `app/index.html`, `app/main.py`, and `app/extended.py` are untouched.
Do not trust this endpoint for a real website or customer database.

The earlier opt-in temporary CRUD behavior of `app.full` is retained by this
entrypoint only when `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY`, and remains
an **unauthenticated fictional testing API**. It has no UI editor. Never deploy
or expose this program publicly. Browser controls render untrusted-looking
fixture strings with `textContent`, not HTML injection.
'''


class UIEmbedReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal['0.1'] = '0.1'
    status: Literal['synthetic_readonly_query_ui_generated_passed'] = 'synthetic_readonly_query_ui_generated_passed'
    fixed_html_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    fixed_source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    prior_crud_report_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    generated_entrypoint: Literal['app.ui:app'] = 'app.ui:app'
    original_templates_unchanged: Literal[True] = True
    customer_database_connected: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    deployment_authorized: Literal[False] = False


def _previous_guards(root: Path) -> str:
    root=_safe_root(root)
    _, query_plan=_preview_guards(root)
    checked={'app/full.py':FULL_SOURCE, 'app/sandbox_crud.py':CRUD_SOURCE,
             'tests/test_embedded_crud.py':__import__('astra_contracts.schema_crud_embed',fromlist=['GENERATED_TEST']).GENERATED_TEST}
    for rel, expected in checked.items():
        path=root/rel
        if path.is_symlink() or not path.is_file() or path.read_text(encoding='utf-8')!=expected:
            raise ValueError('untrusted or absent CRUD source '+rel)
    report_path=root/'data/crud_embed_report.json'
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError('missing CRUD acceptance report')
    report=CRUDEmbedReport.model_validate_json(report_path.read_bytes())
    if report.source_query_plan_sha256!=fingerprint(query_plan):
        raise ValueError('stale CRUD query plan')
    if report.generated_crud_sha256!=hashlib.sha256(CRUD_SOURCE.encode()).hexdigest():
        raise ValueError('stale CRUD source report')
    if (root/'app/main.py').read_text(encoding='utf-8')!=APP or (root/'app/index.html').read_text(encoding='utf-8')!=HTML:
        raise ValueError('protected generated templates changed')
    return hashlib.sha256(report_path.read_bytes()).hexdigest()


def embed_query_ui(root: Path) -> UIEmbedReport:
    root=_safe_root(Path(root))
    report_sha=_previous_guards(root)
    html_digest=hashlib.sha256(QUERY_UI_HTML.encode('utf-8')).hexdigest()
    source=UI_SOURCE.replace('__UI_SHA256__',html_digest)
    files={'app/ui.py':source,'app/query_ui.html':QUERY_UI_HTML,
           'tests/test_embedded_ui.py':GENERATED_TEST,'README_UI.md':README}
    report_rel='data/query_ui_embed_report.json'
    for relative in [*files,report_rel]:
        path=root/relative
        if path.is_symlink() or path.exists():
            raise ValueError('query UI already exists; refusing overwrite')
    for relative,content in files.items():
        with (root/relative).open('x',encoding='utf-8') as handle:
            handle.write(content)
    test=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_embedded_ui.py'],
                        cwd=root,capture_output=True,text=True,timeout=35)
    if test.returncode:
        raise ValueError('generated UI tests failed: '+test.stdout[-1200:]+test.stderr[-600:])
    report=UIEmbedReport(fixed_html_sha256=html_digest,
                         fixed_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                         prior_crud_report_sha256=report_sha)
    with (root/report_rel).open('x',encoding='utf-8') as handle:
        handle.write(report.model_dump_json(indent=2)+'\n')
    return report


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description='Add trusted synthetic sort/filter HTML to generated preview')
    parser.add_argument('existing_generated_temp_preview',type=Path)
    args=parser.parse_args(argv)
    try: report=embed_query_ui(args.existing_generated_temp_preview)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:
        print(f'FAIL: {e}',file=sys.stderr);return 1
    print(report.model_dump_json(indent=2));return 0


if __name__=='__main__':
    raise SystemExit(main())
