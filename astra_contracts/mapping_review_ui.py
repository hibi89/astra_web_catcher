"""Install a review-only observation mapping panel into an isolated fictional app.

All mapping-driven actions remain disabled. Existing generic synthetic query UI
is independent and unmodified. No real site behavior, owned data, or approval.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable
from astra_contracts.observed_ui_mapping import (
    UIActionMappingPlan, UIActionMappingReport, build_ui_mapping,
)
from astra_contracts.schema_query_ui import (
    QUERY_UI_HTML, UI_SOURCE, UIEmbedReport, _previous_guards,
)
from astra_contracts.schema_query_embed import _safe_root


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ReviewItem(ClosedModel):
    link_id: str
    ui_field: str
    label: str
    status: str
    reason: str
    proposed_filter_by: str | None = None
    proposed_filter_value: str | int | None = None
    enabled: Literal[False] = False
    synthetic_illustration_only: Literal[True] = True
    original_site_behavior_verified: Literal[False] = False


class ReviewManifest(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['review_only_all_mapping_actions_disabled'] = 'review_only_all_mapping_actions_disabled'
    physical_table_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_mapping_report_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    evidence_content_authenticated: Literal[False] = False
    owner_database_access_authorized: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    generation_authorized: Literal[False] = False
    mapping_actions_enabled: Literal[False] = False
    items: list[ReviewItem] = Field(min_length=1, max_length=40)

    @model_validator(mode='after')
    def unique_items(self):
        ids = [x.link_id for x in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate link id')
        return self


def build_review_manifest(report: UIActionMappingReport, table: AlternateSyntheticTable,
                          blocked_report: UIActionMappingReport | None = None) -> ReviewManifest:
    """Pure review result: even a candidate remains an INACTIVE suggestion."""
    report = UIActionMappingReport.model_validate(report.model_dump(mode='json'))
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    if report.synthetic_table_sha256 != fingerprint(table):
        raise ValueError('mapping report does not match physical synthetic table')
    if report.status != 'review_only_never_authorized':
        raise ValueError('mapping must remain review-only')
    by_link = {c.link_id: c for c in report.synthetic_preview_candidates}
    if len(by_link) != len(report.synthetic_preview_candidates):
        raise ValueError('duplicate candidates')
    declared = {x.source_field for x in table.bindings}
    items = []
    for finding in report.findings:
        c = by_link.get(finding.link_id)
        if (finding.status == 'synthetic_preview_candidate_unapproved') != (c is not None):
            raise ValueError('finding and candidate disagree')
        if c and (c.query_filter_by not in declared or c.semantics_approved is not False
                  or c.synthetic_illustration_only is not True or c.read_only_route != '/api/rows'):
            raise ValueError('unsafe candidate proposal')
        items.append(ReviewItem(
            link_id=finding.link_id, ui_field=finding.ui_field,
            label='가상 필터 매핑 후보' if c else '관찰 매핑 차단',
            status=finding.status, reason=finding.explanation,
            proposed_filter_by=c.query_filter_by if c else None,
            proposed_filter_value=c.query_filter_value if c else None,
        ))
    if blocked_report is not None:
        blocked_report = UIActionMappingReport.model_validate(blocked_report.model_dump(mode='json'))
        if (blocked_report.status != 'review_only_never_authorized' or
                blocked_report.synthetic_preview_candidates or
                any(x.status == 'synthetic_preview_candidate_unapproved' for x in blocked_report.findings)):
            raise ValueError('secondary blocked report must contain no candidates')
        for f in blocked_report.findings:
            items.append(ReviewItem(link_id=f.link_id, ui_field=f.ui_field,
                                    label='과거 기록만 존재 — 사용 불가', status=f.status,
                                    reason=f.explanation))
    if not items:
        raise ValueError('nothing to review')
    return ReviewManifest(physical_table_sha256=fingerprint(table),
                          source_mapping_report_sha256=fingerprint(report), items=items)


REVIEW_PANEL = '''<section class="panel" id="mapping-review" aria-labelledby="mapping-heading">
<h2 id="mapping-heading">관찰 매핑 검토 · 기능 비활성화</h2>
<p class="muted">아래 항목은 승인된 기능이 아닙니다. 가상 예시와 과거 관찰 기록이며 실제 사이트 기능을 재현했다고 주장하지 않습니다.</p>
<div class="table-wrap"><table aria-label="관찰 근거와 UI 매핑 검토 결과"><thead><tr>
<th>근거 구분</th><th>관찰 필드</th><th>연결된 가상 필드</th><th>판정</th><th>조작</th>
</tr></thead><tbody id="mapping-rows"></tbody></table></div>
<p id="mapping-feedback" class="muted" aria-live="polite">검토용 매핑을 불러오는 중…</p>
</section>'''

REVIEW_JS = '''<script>
'use strict';
(async function reviewOnly() {
  const body=document.getElementById('mapping-rows');
  const feedback=document.getElementById('mapping-feedback');
  try {
    const response=await fetch('/api/review-manifest',{cache:'no-store'});
    if (!response.ok) throw new Error('검토 기록을 확인할 수 없습니다.');
    const manifest=await response.json();
    if (manifest.status!=='review_only_all_mapping_actions_disabled' ||
        manifest.mapping_actions_enabled!==false ||
        manifest.original_site_behavior_verified!==false ||
        manifest.owner_database_access_authorized!==false ||
        !Array.isArray(manifest.items)) throw new Error('승인되지 않은 매핑 정보입니다.');
    body.replaceChildren();
    for (const item of manifest.items) {
      if (item.enabled!==false || item.original_site_behavior_verified!==false ||
          item.synthetic_illustration_only!==true) throw new Error('활성 매핑 발견 — 표시 거부');
      const row=document.createElement('tr');
      for (const value of [item.label,item.ui_field,item.proposed_filter_by ?? '—',item.status]) {
        const cell=document.createElement('td');cell.textContent=String(value);row.appendChild(cell);
      }
      const cell=document.createElement('td');
      const button=document.createElement('button');
      button.type='button';button.textContent='검토 대기';button.disabled=true;
      button.setAttribute('aria-label',item.link_id+' 검토 대기: '+item.reason);
      cell.appendChild(button);row.appendChild(cell);body.appendChild(row);
    }
    feedback.textContent='매핑 '+manifest.items.length+'건 검토 중 · 승인/자동 적용 0건';
  } catch (error) {
    body.replaceChildren();
    feedback.setAttribute('role','alert');
    feedback.textContent=error.message;
  }
})();
</script>'''

REVIEW_HTML = QUERY_UI_HTML.replace('</main>', REVIEW_PANEL + '</main>').replace('</body>', REVIEW_JS + '</body>')
if REVIEW_HTML == QUERY_UI_HTML or REVIEW_HTML.count('id="mapping-review"') != 1:
    raise RuntimeError('unable to construct fixed review-only template')

MAPPED_SOURCE = '''"""Fixed review-only synthetic overlay. No mapping permissions or external DB."""
import hashlib
import json
import os
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
if os.environ.get("ASTRA_ENABLE_SYNTHETIC_CRUD") == "YES_TEMP_ONLY":
    raise RuntimeError("mapped review cannot launch with write-enabled synthetic CRUD")
from app.ui import create_ui_app
from app.extended import FIXTURE_SHA256

ROOT=Path(__file__).resolve().parent.parent
REVIEW_HTML_SHA256="__REVIEW_HTML_SHA256__"
MANIFEST_SHA256="__MANIFEST_SHA256__"


def _trusted(path,sha):
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise HTTPException(503,'synthetic review asset integrity failed')
    return path


def create_mapped_app(base_db_path=None):
    app=create_ui_app(base_db_path,enable_synthetic_crud=False)
    page=ROOT/'app'/'mapped_review.html'
    manifest_path=ROOT/'data'/'review_manifest.json'
    physical_path=ROOT/'data'/'query_physical_fixture.json'

    @app.get('/preview-mapped',include_in_schema=False)
    def review_page():
        _trusted(manifest_path,MANIFEST_SHA256)
        return FileResponse(_trusted(page,REVIEW_HTML_SHA256),media_type='text/html',
                            headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/api/review-manifest',include_in_schema=False)
    def review_manifest():
        _trusted(page,REVIEW_HTML_SHA256)
        _trusted(physical_path,FIXTURE_SHA256)
        path=_trusted(manifest_path,MANIFEST_SHA256)
        data=json.loads(path.read_bytes())
        if (data.get('status')!='review_only_all_mapping_actions_disabled' or
            data.get('mapping_actions_enabled') is not False or
            data.get('original_site_behavior_verified') is not False or
            data.get('owner_database_access_authorized') is not False or
            data.get('generation_authorized') is not False or
            not isinstance(data.get('items'),list) or not data['items'] or
            any(x.get('enabled') is not False or
                x.get('synthetic_illustration_only') is not True or
                x.get('original_site_behavior_verified') is not False
                for x in data['items'])):
            raise HTTPException(503,'review-only policy failed')
        return JSONResponse(data,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
    return app


app=create_mapped_app()
'''


class ReviewEmbedReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['disabled_mapping_review_installed'] = 'disabled_mapping_review_installed'
    generated_entrypoint: Literal['app.mapped:app'] = 'app.mapped:app'
    manifest_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    page_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    synthetic_only: Literal[True] = True
    mapping_actions_enabled: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    customer_database_connected: Literal[False] = False
    deployment_authorized: Literal[False] = False


def embed_review_ui(root: Path, bundle: ObservationBundle,
                    declaration: OwnedSchemaDeclaration, table: AlternateSyntheticTable,
                    plan: UIActionMappingPlan, evidence_root: Path,
                    blocked_report: UIActionMappingReport | None = None) -> ReviewEmbedReport:
    """Single isolated write after verifying full evidence and previous generated app."""
    root = _safe_root(Path(root))
    _previous_guards(root)
    ui_src = UI_SOURCE.replace('__UI_SHA256__', hashlib.sha256(QUERY_UI_HTML.encode()).hexdigest())
    existing = {'app/ui.py':ui_src, 'app/query_ui.html':QUERY_UI_HTML}
    for rel, expected in existing.items():
        path = root / rel
        if path.is_symlink() or not path.is_file() or path.read_text(encoding='utf-8') != expected:
            raise ValueError('prior query UI is missing or tampered: '+rel)
    report_path=root/'data/query_ui_embed_report.json'
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError('missing prior query UI report')
    uireport=UIEmbedReport.model_validate_json(report_path.read_bytes())
    if (uireport.fixed_html_sha256 != hashlib.sha256(QUERY_UI_HTML.encode()).hexdigest() or
        uireport.fixed_source_sha256 != hashlib.sha256(ui_src.encode()).hexdigest()):
        raise ValueError('stale query UI report')
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    physical_file=root/'data/query_physical_fixture.json'
    if physical_file.is_symlink() or not physical_file.is_file():
        raise ValueError('physical fixture missing')
    disk_table=AlternateSyntheticTable.model_validate_json(physical_file.read_bytes())
    if fingerprint(disk_table)!=fingerprint(table):
        raise ValueError('mapping table differs from generated app physical data')
    report=build_ui_mapping(bundle,declaration,table,plan,evidence_root)
    manifest=build_review_manifest(report,table,blocked_report)
    manifest_string=manifest.model_dump_json(indent=2)+'\n'
    digest_manifest=hashlib.sha256(manifest_string.encode()).hexdigest()
    digest_page=hashlib.sha256(REVIEW_HTML.encode()).hexdigest()
    source=MAPPED_SOURCE.replace('__REVIEW_HTML_SHA256__',digest_page).replace('__MANIFEST_SHA256__',digest_manifest)
    output={'app/mapped.py':source,'app/mapped_review.html':REVIEW_HTML,
            'data/review_manifest.json':manifest_string}
    for rel in [*output,'data/mapped_embed_report.json']:
        path=root/rel
        if path.is_symlink() or path.exists():
            raise ValueError('review mapping output already exists — refusing overwrite')
    for rel, value in output.items():
        with (root/rel).open('x',encoding='utf-8') as out:
            out.write(value)
    check=subprocess.run([sys.executable,'-c',
                          'from app.mapped import create_mapped_app; from fastapi.testclient import TestClient; '
                          'c=TestClient(create_mapped_app()); '
                          'assert c.get("/preview-mapped").status_code==200; '
                          'assert c.get("/api/review-manifest").status_code==200; '
                          'assert all(x["enabled"] is False for x in c.get("/api/review-manifest").json()["items"])'],
                         cwd=root,capture_output=True,text=True,timeout=20)
    if check.returncode:
        raise ValueError('generated review app smoke failed: '+check.stderr[-700:])
    embed=ReviewEmbedReport(manifest_sha256=digest_manifest,page_sha256=digest_page,
                            source_sha256=hashlib.sha256(source.encode()).hexdigest())
    with (root/'data/mapped_embed_report.json').open('x',encoding='utf-8') as out:
        out.write(embed.model_dump_json(indent=2)+'\n')
    return embed
