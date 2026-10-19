"""Run real loopback HTTP SQLite → API → browser UI verification in Chromium.

No database file, owner API, external origin, or deployment is used.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import socket
import threading
import time

from playwright.sync_api import sync_playwright
import uvicorn
from astra_contracts.synthetic_sqlite_dashboard import create_synthetic_app


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run(*, fixture: Path, rows_path: Path, chromium: Path | None = None) -> dict:
    schema = json.loads(fixture.read_text(encoding='utf-8'))
    rows = json.loads(rows_path.read_text(encoding='utf-8'))
    app = create_synthetic_app(schema, rows)
    port = _port()
    base = f'http://127.0.0.1:{port}'
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                           log_level='error', access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                raise RuntimeError('demo server did not start')
            time.sleep(.05)
        else:
            raise RuntimeError('demo server startup timeout')
        with sync_playwright() as pw:
            options = {'headless': True}
            if chromium is not None:
                if not chromium.is_file():
                    raise ValueError('Chromium executable missing')
                options['executable_path'] = str(chromium)
            browser = pw.chromium.launch(**options)
            version = browser.version
            try:
                context = browser.new_context(viewport={'width': 1280, 'height': 800})
                page = context.new_page()
                errors, requests = [], []
                page.on('pageerror', lambda exc: errors.append(str(exc)))
                page.on('request', lambda req: requests.append(req.url))
                response = page.goto(base+'/preview', wait_until='load')
                assert response.status == 200
                page.locator('#api-readout[data-connected="true"]').wait_for(timeout=8000)
                assert page.locator('#chart-view circle').count() == len(rows)
                assert page.locator('table tbody tr').count() == len(rows)
                assert any(u.endswith('/preview') for u in requests)
                assert any(u.endswith('/api/demo/series') for u in requests)
                assert all(u.startswith(base+'/') for u in requests), requests
                page.locator('#show-table').click()
                assert page.locator('#table-view').is_visible()
                page.locator('#show-chart').focus()
                page.keyboard.press('Enter')
                assert page.locator('#chart-view').is_visible()
                page.locator('#show-table').focus()
                page.keyboard.press('Space')
                assert page.locator('#table-view').is_visible()
                changed = copy.deepcopy(rows)
                changed[0][schema['proposed_bindings']['numeric_measure']] = 666.125
                app.state.synthetic_store.replace_rows_for_local_test(changed)
                page.reload(wait_until='load')
                page.locator('#api-readout[data-connected="true"]').wait_for(timeout=8000)
                page.locator('#show-table').click()
                assert page.locator('table tbody tr').count() == len(rows)
                assert page.get_by_role('cell', name='666.125').count() == 1
                assert not page.get_by_role('cell', name='18.5').count()
                assert not errors, errors
                assert all(u.startswith(base+'/') for u in requests), requests
                # Fail closed on an API/HTML mismatch, even when count remains identical.
                def corrupt(response_route):
                    response_route.fulfill(status=200, content_type='application/json',
                                          body=json.dumps({'source_kind':'synthetic_fixture',
                                                           'storage':'sqlite_in_memory',
                                                           'count':len(rows),
                                                           'mapping_approved':False,
                                                           'owner_schema_connected':False,
                                                           'generation_contract':'blocked_pending_review',
                                                           'snapshot_sha256':'0'*64}))
                page.route('**/api/demo/series', corrupt)
                page.reload(wait_until='load')
                page.locator('#api-readout[data-connected="false"]').wait_for(timeout=8000)
                page.unroute('**/api/demo/series', corrupt)
                page.close()
                context.close()
            finally:
                browser.close()
        return {'status':'PASS', 'engine':'Chromium', 'version':version,
                'actual_loopback_http':True, 'actual_sqlite_in_memory':True,
                'http_api_called_by_browser':True, 'chart_table_controls':'PASS',
                'sqlite_update_reflected_in_browser':'PASS',
                'mismatched_api_snapshot_blocked':'PASS',
                'external_requests':0, 'javascript_errors':0,
                'owner_db_connected':False, 'generation_authorized':False,
                'deployment_authorized':False,
                'generation_contract':'blocked_pending_review'}
    finally:
        server.should_exit = True
        thread.join(timeout=8)
        if thread.is_alive():
            raise RuntimeError('loopback synthetic demo server did not shut down')


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--chromium', type=Path)
    a = p.parse_args(argv)
    print(json.dumps(run(fixture=a.fixture, rows_path=a.rows, chromium=a.chromium), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
