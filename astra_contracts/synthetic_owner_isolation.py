"""Synthetic owner-shaped field mappings and session-scoped SQLite Chart/Table demo.

Only fabricated demo owners and data. No customer schema, credentials, or public
login/write route. Sessions are issued only by an in-process local test driver.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import json
import re
import secrets
import sqlite3
import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from astra_contracts.synthetic_chart_table_preview import _safe_rows, render_preview
from astra_contracts.synthetic_sqlite_dashboard import HEADERS, _digest
from astra_contracts.synthetic_timeseries_review import review

COOKIE = 'astra_synthetic_owner_session'
DEMO_OWNER = re.compile(r'^demo_[a-z0-9_]{1,24}$')
MAX_OWNERS = 5


def _declaration(schema: dict[str, Any]) -> tuple[dict[str, Any], list[str], str, dict]:
    """Reconcile a *declared*, synthetic owner column to the four UI semantic roles."""
    if not isinstance(schema, dict) or set(schema) != {
        'source_kind', 'dataset_id', 'columns', 'proposed_bindings',
        'owner_binding', 'owner_ids',
    }:
        raise ValueError('exact synthetic owner declaration required')
    if schema['source_kind'] != 'synthetic_fixture':
        raise ValueError('only fabricated synthetic fixture supported')
    owners = schema['owner_ids']
    if not isinstance(owners, list) or not 2 <= len(owners) <= MAX_OWNERS or any(
        not isinstance(o, str) or not DEMO_OWNER.fullmatch(o) for o in owners
    ) or len(set(owners)) != len(owners):
        raise ValueError('unique demo_ owner IDs required (2..5)')
    owner_field = schema['owner_binding']
    if not isinstance(owner_field, str):
        raise ValueError('explicit synthetic owner field required')
    columns = schema['columns']
    if not isinstance(columns, list):
        raise ValueError('invalid synthetic columns')
    selected = [x for x in columns if isinstance(x, dict) and x.get('name') == owner_field]
    if len(selected) != 1 or set(selected[0]) != {'name', 'kind'} or selected[0]['kind'] != 'string':
        raise ValueError('owner field must be one declared string column')
    if not isinstance(schema['proposed_bindings'], dict) or owner_field in schema['proposed_bindings'].values():
        raise ValueError('owner field cannot be a chart/table semantic role')
    mapped_schema = {
        'source_kind': 'synthetic_fixture',
        'dataset_id': schema['dataset_id'],
        'columns': [x for x in columns if isinstance(x, dict) and x.get('name') != owner_field],
        'proposed_bindings': schema['proposed_bindings'],
    }
    diagnostic = review(mapped_schema)
    if diagnostic['missing_or_incompatible']:
        raise ValueError('missing/incompatible synthetic roles: ' + ', '.join(diagnostic['missing_or_incompatible']))
    # This one narrow preview intentionally drops no unknown columns from the API.
    if len(mapped_schema['columns']) != 4 or set(schema['proposed_bindings'].values()) != {
        c['name'] for c in mapped_schema['columns']
    }:
        raise ValueError('exactly four distinct mapped fields required')
    return mapped_schema, owners[:], owner_field, diagnostic


class DemoOwnerStore:
    """One shared ephemeral SQLite with unavoidable owner predicates on every read."""

    def __init__(self, declaration: dict, input_rows: list[dict]):
        # Freeze caller objects and reject NaN/Infinity in JSON.
        frozen = json.loads(json.dumps(declaration, allow_nan=False))
        self.schema, owner_ids, self.owner_field, self.diagnostic = _declaration(frozen)
        self.owner_ids = tuple(owner_ids)
        self._lock = threading.RLock()
        self._closed = False
        if not isinstance(input_rows, list) or not input_rows:
            raise ValueError('demo owner rows required')
        frozen_rows = json.loads(json.dumps(input_rows, allow_nan=False))
        owners_to_rows = self._partition_and_validate(frozen_rows)
        self._conn = sqlite3.connect(':memory:', check_same_thread=False)
        self._conn.execute('PRAGMA foreign_keys=ON')
        try:
            self._conn.execute('''CREATE TABLE demo_owner_series (
                owner_id TEXT NOT NULL,
                entity TEXT NOT NULL,
                period TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (owner_id, entity, period)
            )''')
            for owner_id, records in owners_to_rows.items():
                self._insert_owner(owner_id, records)
        except Exception:
            self._conn.close()
            raise

    def _partition_and_validate(self, rows: list[dict]) -> dict[str, list[dict]]:
        allowed = {x['name'] for x in self.schema['columns']} | {self.owner_field}
        groups: dict[str, list[dict]] = {owner: [] for owner in self.owner_ids}
        for row in rows:
            if not isinstance(row, dict) or set(row) != allowed:
                raise ValueError('row differs from declared synthetic owner columns')
            owner = row[self.owner_field]
            if not isinstance(owner, str) or owner not in groups:
                raise ValueError('undeclared synthetic owner in row')
            groups[owner].append({key: value for key, value in row.items() if key != self.owner_field})
        for owner, group in groups.items():
            if not group:
                raise ValueError('every declared demo owner needs rows')
            validated, _, _, _ = _safe_rows(self.schema, group)
            groups[owner] = validated
        return groups

    def _insert_owner(self, owner: str, rows: list[dict]) -> None:
        bindings = self.schema['proposed_bindings']
        entity = bindings['entity_identifier']
        period = bindings['time_period']
        self._conn.executemany(
            'INSERT INTO demo_owner_series(owner_id, entity, period, payload) VALUES(?,?,?,?)',
            ((owner, row[entity], row[period],
              json.dumps(row, allow_nan=False, ensure_ascii=False)) for row in rows),
        )
        self._conn.commit()

    def snapshot(self, owner: str) -> list[dict]:
        with self._lock:
            if self._closed:
                raise RuntimeError('demo owner store closed')
            if owner not in self.owner_ids:
                raise ValueError('unknown demo owner')
            raw = self._conn.execute(
                'SELECT payload FROM demo_owner_series WHERE owner_id=? ORDER BY period,entity',
                (owner,),
            ).fetchall()
            return [json.loads(item[0]) for item in raw]

    def replace_owner_for_local_test(self, owner: str, rows: list[dict]) -> None:
        """In-process test-driver capability only; no HTTP route to call this method."""
        if owner not in self.owner_ids or not isinstance(rows, list):
            raise ValueError('invalid demo owner or rows')
        # A single-owner replacement must not supply foreign owner data.
        checked = self._partition_one(owner, rows)
        with self._lock:
            if self._closed:
                raise RuntimeError('demo owner store closed')
            try:
                self._conn.execute('BEGIN IMMEDIATE')
                self._conn.execute('DELETE FROM demo_owner_series WHERE owner_id=?', (owner,))
                mapping = self.schema['proposed_bindings']
                self._conn.executemany(
                    'INSERT INTO demo_owner_series(owner_id,entity,period,payload) VALUES(?,?,?,?)',
                    ((owner, row[mapping['entity_identifier']], row[mapping['time_period']],
                      json.dumps(row, ensure_ascii=False, allow_nan=False)) for row in checked),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def _partition_one(self, owner: str, rows: list[dict]) -> list[dict]:
        # Accept only owner-scoped records (including the explicitly bound owner field).
        if not rows or any(not isinstance(row, dict) or row.get(self.owner_field) != owner for row in rows):
            raise ValueError('owner-scoped demo rows required')
        trimmed = [{key: val for key, val in row.items() if key != self.owner_field} for row in rows]
        checked, _, _, _ = _safe_rows(self.schema, trimmed)
        return checked

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._conn.close()
                self._closed = True


class InProcessDemoSessions:
    """Unforgeable owner sessions, issued only to the local E2E/test driver."""

    def __init__(self, owners: tuple[str, ...]):
        self._owners = owners
        self._sessions: dict[str, str] = {}
        self._lock = threading.RLock()

    def issue_for_local_test(self, owner: str) -> str:
        if owner not in self._owners:
            raise ValueError('unknown demo owner')
        raw = secrets.token_urlsafe(32)
        digest = hashlib.sha256(raw.encode('ascii')).hexdigest()
        with self._lock:
            self._sessions[digest] = owner
        return raw

    def resolve(self, raw: str | None) -> str | None:
        if not raw or len(raw) > 128:
            return None
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        with self._lock:
            return self._sessions.get(digest)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


def create_owner_like_app(declaration: dict, rows: list[dict]) -> FastAPI:
    """Synthetic-only owner-scoped API and server-rendered read-only Chart/Table UI."""
    store = DemoOwnerStore(declaration, rows)
    sessions = InProcessDemoSessions(store.owner_ids)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            store.close()
            sessions.clear()

    app = FastAPI(title='ASTRA local synthetic owner isolation demonstration',
                  openapi_url=None, docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.demo_owner_store = store
    app.state.demo_sessions = sessions

    def principal(request: Request) -> str:
        if request.query_params:
            raise HTTPException(status_code=400, detail='unexpected query parameters')
        owner = sessions.resolve(request.cookies.get(COOKIE))
        if owner is None:
            raise HTTPException(status_code=401, detail='unauthenticated local synthetic demo')
        return owner

    def api_record(owner: str):
        records = store.snapshot(owner)
        return JSONResponse({
            'source_kind': 'synthetic_fixture', 'storage': 'sqlite_in_memory',
            'owner_scope': owner, 'dataset_id': store.schema['dataset_id'],
            'count': len(records), 'rows': records, 'snapshot_sha256': _digest(records),
            'proposed_bindings': dict(store.schema['proposed_bindings']),
            'owner_binding_status': 'structurally_compatible_unapproved',
            'mapping_approved': False, 'owner_schema_connected': False,
            'code_generation_authorized': False, 'deployment_authorized': False,
            'generation_contract': 'blocked_pending_review',
        }, headers=HEADERS)

    @app.get('/api/demo/series')
    def own_series(request: Request):
        return api_record(principal(request))

    @app.get('/api/demo/owners/{requested_owner}/series')
    def scoped_series(requested_owner: str, request: Request):
        owner = principal(request)
        if requested_owner != owner:
            raise HTTPException(status_code=404, detail='not found')
        return api_record(owner)

    @app.get('/preview', response_class=HTMLResponse)
    def preview(request: Request):
        owner = principal(request)
        records = store.snapshot(owner)
        html = render_preview(store.schema, records)
        if html.count('<head>') != 1 or html.count('</body>') != 1:
            raise RuntimeError('unexpected synthetic preview structure')
        html = html.replace('<head>', '<head><meta name="synthetic-snapshot-sha256" content="'
                            + _digest(records) + '">')
        old = 'Network: none. Owner DB: disconnected.'
        if html.count(old) != 1:
            raise RuntimeError('synthetic preview provenance marker changed')
        html = html.replace(old, 'Network: localhost synthetic demo only. Owner DB: disconnected.')
        script = '''<script>
'use strict';
const status=document.createElement('p');
status.id='api-readout';status.setAttribute('role','status');
status.textContent='Checking synthetic owner-scoped API...';
document.querySelector('main').appendChild(status);
fetch('/api/demo/series',{cache:'no-store',credentials:'same-origin'})
.then(resp=>{if(!resp.ok)throw Error('local API error');return resp.json();})
.then(data=>{
  if(data.source_kind!=='synthetic_fixture'||data.storage!=='sqlite_in_memory'||
     data.owner_binding_status!=='structurally_compatible_unapproved'||
     data.mapping_approved!==false||data.owner_schema_connected!==false||
     data.code_generation_authorized!==false||data.deployment_authorized!==false||
     data.generation_contract!=='blocked_pending_review'||
     data.count!==document.querySelectorAll('#table-view tbody tr').length||
     data.snapshot_sha256!==document.querySelector('meta[name="synthetic-snapshot-sha256"]').content){
    throw Error('synthetic scoped API snapshot mismatch');
  }
  status.dataset.connected='true';
  status.textContent='Synthetic scoped API: '+data.count+' rows (REVIEW ONLY)';
})
.catch(()=>{status.dataset.connected='false';
  status.textContent='Synthetic API unavailable or snapshot mismatch';});
</script>'''
        html = html.replace('</body>', script + '</body>')
        headers = dict(HEADERS)
        headers['Content-Security-Policy'] = (
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "img-src 'none'; connect-src 'self'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'"
        )
        return HTMLResponse(html, headers=headers)

    return app
