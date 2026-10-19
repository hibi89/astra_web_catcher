"""Disposable, in-memory SQLite to read-only HTTP/API and synthetic chart/table UI.

This isolated demo accepts only validated synthetic fixtures, never an owner DB URL,
filesystem DB location, production schema, write HTTP API, or deployment command.
No database content survives app shutdown. The same SQLite snapshot is queried by
both the JSON GET endpoint and server-rendered HTML preview.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import json
import sqlite3
import threading
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from astra_contracts.synthetic_chart_table_preview import _safe_rows, render_preview


class SyntheticMemoryStore:
    """Dedicated private SQLite :memory: instance; server-side writes only."""

    def __init__(self, schema: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        # Freeze callers' mutable input; JSON is also the intended wire format.
        self.schema = json.loads(json.dumps(schema, allow_nan=False))
        validated, _, _, _ = _safe_rows(self.schema, rows)
        self._bindings = dict(self.schema['proposed_bindings'])
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(':memory:', check_same_thread=False)
        self._connection.execute('PRAGMA foreign_keys=ON')
        self._connection.execute('''CREATE TABLE synthetic_rows (
            entity TEXT NOT NULL,
            period TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (entity, period)
        )''')
        self._closed = False
        self._replace_validated(validated)

    def _replace_validated(self, validated: list[dict[str, Any]]) -> None:
        entity_col = self._bindings['entity_identifier']
        period_col = self._bindings['time_period']
        with self._lock:
            if self._closed:
                raise RuntimeError('synthetic store closed')
            try:
                self._connection.execute('BEGIN IMMEDIATE')
                self._connection.execute('DELETE FROM synthetic_rows')
                self._connection.executemany(
                    'INSERT INTO synthetic_rows (entity, period, payload) VALUES (?, ?, ?)',
                    ((row[entity_col], row[period_col],
                      json.dumps(row, ensure_ascii=False, allow_nan=False)) for row in validated),
                )
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def replace_rows_for_local_test(self, rows: list[dict[str, Any]]) -> None:
        """In-process, test-driver-only reset; NOT exposed as an HTTP endpoint."""
        validated, _, _, _ = _safe_rows(self.schema, rows)
        self._replace_validated(validated)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._closed:
                raise RuntimeError('synthetic store closed')
            records = self._connection.execute(
                'SELECT payload FROM synthetic_rows ORDER BY period, entity'
            ).fetchall()
        return [json.loads(rec[0]) for rec in records]

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True


def _digest(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
           'Referrer-Policy': 'no-referrer'}


def create_synthetic_app(schema: dict[str, Any], rows: list[dict[str, Any]]) -> FastAPI:
    """Build isolated read-only demonstration app with no production database target."""
    store = SyntheticMemoryStore(schema, rows)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title='ASTRA synthetic SQLite Chart/Table demo',
                  docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.synthetic_store = store  # Only local test driver can replace synthetic data.

    @app.get('/api/demo/series')
    def series():
        records = store.snapshot()
        return JSONResponse({
            'source_kind': 'synthetic_fixture', 'storage': 'sqlite_in_memory',
            'dataset_id': store.schema['dataset_id'], 'count': len(records),
            'snapshot_sha256': _digest(records),
            'rows': records, 'proposed_bindings': dict(store._bindings),
            'mapping_approved': False, 'owner_schema_connected': False,
            'generation_contract': 'blocked_pending_review',
        }, headers=HEADERS)

    @app.get('/preview', response_class=HTMLResponse)
    def preview():
        records = store.snapshot()
        html = render_preview(store.schema, records)
        if html.count('<head>') != 1:
            raise RuntimeError('unexpected preview HTML head')
        html = html.replace('<head>', '<head><meta name="synthetic-snapshot-sha256" '
                            'content="' + _digest(records) + '">')
        # No unpinned, invented provenance claim. The page *does* use local HTTP.
        old = 'Network: none. Owner DB: disconnected.'
        if html.count(old) != 1:
            raise RuntimeError('preview provenance label changed unexpectedly')
        html = html.replace(old, 'Network: localhost API only. Owner DB: disconnected.')
        verify_api = '''<script>
'use strict';
const apiReadout=document.createElement('p');
apiReadout.id='api-readout';apiReadout.setAttribute('role','status');
apiReadout.textContent='Checking the disposable local SQLite API...';
document.querySelector('main').appendChild(apiReadout);
fetch('/api/demo/series',{cache:'no-store'})
.then(response=>{if(!response.ok)throw new Error('API failed');return response.json();})
.then(payload=>{
  if(payload.source_kind!=='synthetic_fixture'||payload.storage!=='sqlite_in_memory'||
     payload.mapping_approved!==false||payload.owner_schema_connected!==false||
     payload.generation_contract!=='blocked_pending_review'||
     payload.count!==document.querySelectorAll('#table-view tbody tr').length||
     payload.snapshot_sha256!==document.querySelector('meta[name="synthetic-snapshot-sha256"]').content){
       throw new Error('Local API and HTML snapshot differ');
     }
  apiReadout.dataset.connected='true';
  apiReadout.textContent='Local SQLite API: '+payload.count+' synthetic rows loaded (review only)';
})
.catch(()=>{apiReadout.dataset.connected='false';
           apiReadout.textContent='Local SQLite API unavailable or snapshot mismatch';});
</script>'''
        # Inject constant, parameter-free JS after renderer's script. JSON is never
        # interpolated into JS; dynamic text remains escaped by the existing renderer.
        if html.count('</body>') != 1:
            raise RuntimeError('unexpected preview HTML structure')
        html = html.replace('</body>', verify_api + '</body>')
        headers = dict(HEADERS)
        headers['Content-Security-Policy'] = (
            "default-src 'none'; script-src 'unsafe-inline'; "
            "style-src 'unsafe-inline'; img-src 'none'; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        return HTMLResponse(html, headers=headers)

    return app
