"""Present *unverified* before/after provenance in a generated fictional review UI.

No snapshot contents are copied into the app. A ledger is rebuilt from registered
local bytes before installing a digest-pinned, disabled read-only review panel.
No original-site authenticity, approval, authorization or permissions are inferred.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from astra_contracts.capture_transition_ledger import (
    TransitionLedger, TransitionPlan, build_transition_ledger,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.mapping_review_ui import (
    REVIEW_HTML, MAPPED_SOURCE, ReviewEmbedReport,
)
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_query_embed import _safe_root
from astra_contracts.schema_query_ui import _previous_guards

HEX64 = r'^[0-9a-f]{64}$'


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class DisplayFinding(ClosedModel):
    transition_id: str
    observation_id: str
    before_capture_id: str
    after_capture_id: str
    changed_field: str
    status: Literal[
        'paired_bytes_present_unverified', 'source_claim_unconfirmed',
        'missing_or_mismatched_action', 'missing_comparable_before_after',
        'unchanged_claimed_field', 'capture_order_invalid',
        'incomparable_capture_kinds',
    ]
    explanation: str
    enabled: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    evidence_authenticity_verified: Literal[False] = False


class DisplayManifest(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['offline_capture_pair_review_only'] = 'offline_capture_pair_review_only'
    source_ledger_sha256: str = Field(pattern=HEX64)
    original_bundle_sha256: str = Field(pattern=HEX64)
    intake_manifest_sha256: str = Field(pattern=HEX64)
    plan_sha256: str = Field(pattern=HEX64)
    byte_integrity_checked_at_build: Literal[True] = True
    capture_files_rechecked_at_request: Literal[False] = False
    fictional_demo_only: Literal[True] = True
    original_site_behavior_verified: Literal[False] = False
    evidence_authenticity_verified: Literal[False] = False
    semantic_approval_granted: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    ui_controls_enabled: Literal[False] = False
    owner_database_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False
    human_review_required: Literal[True] = True
    findings: list[DisplayFinding] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_findings(self):
        ids = [x.transition_id for x in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate transition IDs')
        return self


def build_display_manifest(ledger: TransitionLedger) -> DisplayManifest:
    """Reduce to safe metadata: do not expose claimed before/after values or source bytes."""
    ledger = TransitionLedger.model_validate(ledger.model_dump(mode='json'))
    if ledger.status != 'evidence_pair_triage_only' or not ledger.byte_integrity_checked:
        raise ValueError('transition ledger not eligible for display')
    findings = [DisplayFinding(
        transition_id=x.transition_id, observation_id=x.observation_id,
        before_capture_id=x.before_capture_id, after_capture_id=x.after_capture_id,
        changed_field=x.changed_field, status=x.status, explanation=x.explanation,
    ) for x in ledger.findings]
    return DisplayManifest(
        source_ledger_sha256=fingerprint(ledger),
        original_bundle_sha256=ledger.original_bundle_sha256,
        intake_manifest_sha256=ledger.intake_manifest_sha256,
        plan_sha256=ledger.plan_sha256,
        findings=findings,
    )


TRANSITION_PANEL = '''<section class="panel" id="transition-review" aria-labelledby="transition-heading">
<h2 id="transition-heading">클릭 전·후 증거 장부 · 전부 검토 대기</h2>
<p class="muted">첨부된 파일의 바이트·순서·주장 구조를 작성 시점에 검사한 결과입니다. 원본 사이트 방문, 화면 의미, 실제 클릭 동작 또는 승인 사실은 확인하지 않았습니다.</p>
<div class="table-wrap"><table aria-label="미승인 전후 캡처 증거 검토 장부"><thead><tr>
<th>전환 ID</th><th>관찰 항목</th><th>전/후 캡처 ID</th><th>변화 주장 필드</th><th>구조 검사 결과</th><th>조작</th>
</tr></thead><tbody id="transition-rows"></tbody></table></div>
<p id="transition-feedback" class="muted" aria-live="polite">전후 캡처 장부를 불러오는 중…</p>
</section>'''

TRANSITION_JS = '''<script>
'use strict';
(async function transitionReviewOnly() {
  const body=document.getElementById('transition-rows');
  const feedback=document.getElementById('transition-feedback');
  try {
    const response=await fetch('/api/transition-ledger',{cache:'no-store'});
    if (!response.ok) throw new Error('증거 장부를 확인할 수 없습니다.');
    const ledger=await response.json();
    if (ledger.status!=='offline_capture_pair_review_only' ||
        ledger.byte_integrity_checked_at_build!==true ||
        ledger.capture_files_rechecked_at_request!==false ||
        ledger.fictional_demo_only!==true ||
        ledger.original_site_behavior_verified!==false ||
        ledger.evidence_authenticity_verified!==false ||
        ledger.semantic_approval_granted!==false ||
        ledger.ui_controls_enabled!==false ||
        ledger.owner_database_access_authorized!==false ||
        ledger.deployment_authorized!==false ||
        ledger.human_review_required!==true ||
        !Array.isArray(ledger.findings) || ledger.findings.length===0)
      throw new Error('검토 정책에 맞지 않는 장부입니다.');
    body.replaceChildren();
    for (const finding of ledger.findings) {
      if (finding.enabled!==false || finding.original_site_behavior_verified!==false ||
          finding.evidence_authenticity_verified!==false)
        throw new Error('승인되지 않은 전후 캡처 기능 발견 — 표시 거부');
      const row=document.createElement('tr');
      const fields=[finding.transition_id,finding.observation_id,
        finding.before_capture_id+' → '+finding.after_capture_id,
        finding.changed_field,finding.status];
      for (const value of fields) {
        const cell=document.createElement('td');
        cell.textContent=String(value);row.appendChild(cell);
      }
      const cell=document.createElement('td');
      const button=document.createElement('button');
      button.type='button';button.textContent='근거 검토 필요';button.disabled=true;
      button.setAttribute('aria-label',String(finding.transition_id)+' 기능 비활성: '+String(finding.explanation));
      cell.appendChild(button);row.appendChild(cell);body.appendChild(row);
    }
    feedback.textContent='전후 쌍 '+ledger.findings.length+'건 · 기능 활성화 0건 · 원본 동작 미검증';
  } catch(error) {
    body.replaceChildren();feedback.setAttribute('role','alert');feedback.textContent=error.message;
  }
})();
</script>'''

TRANSITION_HTML = REVIEW_HTML.replace('</main>', TRANSITION_PANEL + '</main>').replace(
    '</body>', TRANSITION_JS + '</body>')
if TRANSITION_HTML == REVIEW_HTML or TRANSITION_HTML.count('id="transition-review"') != 1:
    raise RuntimeError('transition review panel insertion failed')

TRANSITION_SOURCE = '''"""Disabled provenance report panel for a generated fictional app."""
import hashlib
import json
import os
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
if os.environ.get('ASTRA_ENABLE_SYNTHETIC_CRUD') == 'YES_TEMP_ONLY':
    raise RuntimeError('transition review cannot launch with write-enabled CRUD')
from app.mapped import create_mapped_app
from app.extended import FIXTURE_SHA256

ROOT=Path(__file__).resolve().parent.parent
PAGE_SHA256='__PAGE_SHA256__'
LEDGER_SHA256='__LEDGER_SHA256__'
MAPPED_SOURCE_SHA256='__MAPPED_SOURCE_SHA256__'
MAPPED_PAGE_SHA256='__MAPPED_PAGE_SHA256__'
MAPPED_MANIFEST_SHA256='__MAPPED_MANIFEST_SHA256__'


def _checked(path,digest):
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise HTTPException(503,'unverified synthetic transition review asset')
    return path


def _assets():
    _checked(ROOT/'app'/'mapped.py',MAPPED_SOURCE_SHA256)
    _checked(ROOT/'app'/'mapped_review.html',MAPPED_PAGE_SHA256)
    _checked(ROOT/'data'/'review_manifest.json',MAPPED_MANIFEST_SHA256)
    _checked(ROOT/'data'/'query_physical_fixture.json',FIXTURE_SHA256)
    _checked(ROOT/'app'/'transition_review.html',PAGE_SHA256)
    return _checked(ROOT/'data'/'transition_review_manifest.json',LEDGER_SHA256)


def create_transition_app(base_db_path=None):
    app=create_mapped_app(base_db_path)

    @app.get('/preview-transitions',include_in_schema=False)
    def transition_page():
        _assets()
        return FileResponse(ROOT/'app'/'transition_review.html',media_type='text/html',
                            headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/api/transition-ledger',include_in_schema=False)
    def transition_ledger():
        payload=json.loads(_assets().read_bytes())
        if (payload.get('status')!='offline_capture_pair_review_only' or
            payload.get('byte_integrity_checked_at_build') is not True or
            payload.get('capture_files_rechecked_at_request') is not False or
            payload.get('fictional_demo_only') is not True or
            payload.get('original_site_behavior_verified') is not False or
            payload.get('evidence_authenticity_verified') is not False or
            payload.get('semantic_approval_granted') is not False or
            payload.get('reviewer_identity_verified') is not False or
            payload.get('ui_controls_enabled') is not False or
            payload.get('owner_database_access_authorized') is not False or
            payload.get('deployment_authorized') is not False or
            payload.get('human_review_required') is not True or
            not isinstance(payload.get('findings'),list) or not payload['findings'] or
            any(x.get('enabled') is not False or
                x.get('original_site_behavior_verified') is not False or
                x.get('evidence_authenticity_verified') is not False
                for x in payload['findings'])):
            raise HTTPException(503,'transition provenance policy violation')
        return JSONResponse(payload,headers={'Cache-Control':'no-store',
                                            'X-Content-Type-Options':'nosniff'})
    return app


app=create_transition_app()
'''


class TransitionEmbedReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['unverified_transition_review_installed'] = 'unverified_transition_review_installed'
    entrypoint: Literal['app.transitions:app'] = 'app.transitions:app'
    page_sha256: str = Field(pattern=HEX64)
    manifest_sha256: str = Field(pattern=HEX64)
    source_sha256: str = Field(pattern=HEX64)
    source_ledger_sha256: str = Field(pattern=HEX64)
    enabled_actions: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    customer_db_connected: Literal[False] = False


def embed_transition_review_ui(root: Path, bundle: ObservationBundle,
                               intake_dir: Path, plan: TransitionPlan) -> TransitionEmbedReport:
    """Install no-write review page after verifying intake and protected mapping assets."""
    root = _safe_root(Path(root))
    _previous_guards(root)
    original_paths = ['app/mapped.py', 'app/mapped_review.html',
                      'data/review_manifest.json', 'data/mapped_embed_report.json']
    for name in original_paths:
        asset=root/name
        if asset.is_symlink() or not asset.is_file():
            raise ValueError('missing or symlinked mapped review: '+name)
    old_report = ReviewEmbedReport.model_validate_json((root/'data/mapped_embed_report.json').read_bytes())
    prior_manifest=(root/'data/review_manifest.json').read_bytes()
    prior_page=(root/'app/mapped_review.html').read_bytes()
    prior_source=(root/'app/mapped.py').read_bytes()
    actual_manifest=hashlib.sha256(prior_manifest).hexdigest()
    actual_page=hashlib.sha256(prior_page).hexdigest()
    expected_source = MAPPED_SOURCE.replace('__REVIEW_HTML_SHA256__',actual_page).replace(
        '__MANIFEST_SHA256__',actual_manifest)
    if (actual_page != old_report.page_sha256 or
        actual_manifest != old_report.manifest_sha256 or
        hashlib.sha256(prior_source).hexdigest()!=old_report.source_sha256 or
        prior_page != REVIEW_HTML.encode('utf-8') or
        prior_source != expected_source.encode('utf-8')):
        raise ValueError('prior mapped review was tampered or reported hashes stale')
    ledger=build_transition_ledger(bundle,Path(intake_dir),plan)
    manifest=build_display_manifest(ledger)
    manifest_bytes=(manifest.model_dump_json(indent=2)+'\n').encode('utf-8')
    digest_manifest=hashlib.sha256(manifest_bytes).hexdigest()
    digest_page=hashlib.sha256(TRANSITION_HTML.encode('utf-8')).hexdigest()
    replacements={
        '__PAGE_SHA256__':digest_page,
        '__LEDGER_SHA256__':digest_manifest,
        '__MAPPED_SOURCE_SHA256__':hashlib.sha256(prior_source).hexdigest(),
        '__MAPPED_PAGE_SHA256__':actual_page,
        '__MAPPED_MANIFEST_SHA256__':actual_manifest,
    }
    source=TRANSITION_SOURCE
    for placeholder,digest in replacements.items():
        source=source.replace(placeholder,digest)
    report=TransitionEmbedReport(page_sha256=digest_page,manifest_sha256=digest_manifest,
                                 source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                                 source_ledger_sha256=fingerprint(ledger))
    outputs={
        'app/transitions.py':source.encode('utf-8'),
        'app/transition_review.html':TRANSITION_HTML.encode('utf-8'),
        'data/transition_review_manifest.json':manifest_bytes,
        'data/transition_embed_report.json':(report.model_dump_json(indent=2)+'\n').encode('utf-8'),
    }
    for relative in outputs:
        target=root/relative
        if target.is_symlink() or target.exists():
            raise ValueError('transition review output already exists; refusing overwrite')
    for relative,content in outputs.items():
        with (root/relative).open('xb') as fp:
            fp.write(content)
    check=subprocess.run([sys.executable,'-c',
       "from fastapi.testclient import TestClient;from app.transitions import create_transition_app;"
       "c=TestClient(create_transition_app());"
       "assert c.get('/preview-transitions').status_code==200;"
       "x=c.get('/api/transition-ledger').json();"
       "assert x['ui_controls_enabled'] is False and len(x['findings'])>0;"
       "assert c.get('/api/review-manifest').status_code==200;"
       "assert c.post('/api/items',json={}).status_code==405;"
       "assert c.get('/sandbox/api/items').status_code==404",
       ],cwd=root,capture_output=True,text=True,timeout=25)
    if check.returncode:
        raise ValueError('generated transition preview smoke failed: '+check.stderr[-850:])
    return report
