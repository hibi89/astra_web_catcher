"""Real Chromium + loopback HTTP test of synthetic two-owner session isolation.

Only demo_ identities supplied in memory by the local test driver. Never deploy.
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

from astra_contracts.synthetic_owner_isolation import COOKIE, create_owner_like_app


def _port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run(*, schema_path: Path, rows_path: Path) -> dict:
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    rows = json.loads(rows_path.read_text(encoding='utf-8'))
    app = create_owner_like_app(schema, rows)
    token_a = app.state.demo_sessions.issue_for_local_test('demo_alpha')
    token_b = app.state.demo_sessions.issue_for_local_test('demo_beta')
    port = _port()
    base = f'http://127.0.0.1:{port}'
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                           log_level='error', access_log=False))
    runner = threading.Thread(target=server.run, daemon=True)
    runner.start()
    try:
        for _ in range(120):
            if server.started:
                break
            if not runner.is_alive():
                raise RuntimeError('synthetic owner demo server exited during startup')
            time.sleep(.05)
        else:
            raise RuntimeError('synthetic owner demo server startup timeout')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            version = browser.version
            try:
                screens = {}
                for owner, token, own_canary, forbidden_canary in (
                    ('demo_alpha', token_a, 'ALPHA_CANARY', 'BETA_CANARY'),
                    ('demo_beta', token_b, 'BETA_CANARY', 'ALPHA_CANARY'),
                ):
                    ctx = browser.new_context(viewport={'width':1280, 'height':800})
                    ctx.add_cookies([{'name':COOKIE, 'value':token, 'url':base,
                                      'httpOnly':True, 'sameSite':'Strict'}])
                    page = ctx.new_page()
                    errors, requests = [], []
                    page.on('pageerror', lambda exc: errors.append(str(exc)))
                    page.on('request', lambda req: requests.append(req.url))
                    response = page.goto(base+'/preview', wait_until='load')
                    assert response.status == 200, (owner, response.status)
                    page.locator('#api-readout[data-connected="true"]').wait_for(timeout=10000)
                    assert page.locator('#chart-view circle').count() == 3
                    assert page.locator('table tbody tr').count() == 3
                    assert own_canary in page.content()
                    assert forbidden_canary not in page.content()
                    assert page.evaluate('document.cookie') == '', 'HttpOnly cookie leaked into JS'
                    page.locator('#show-table').click()
                    assert page.locator('#table-view').is_visible()
                    page.locator('#show-chart').focus()
                    page.keyboard.press('Enter')
                    assert page.locator('#chart-view').is_visible()
                    page.locator('#show-table').focus()
                    page.keyboard.press('Space')
                    assert page.locator('#table-view').is_visible()
                    other = 'demo_beta' if owner == 'demo_alpha' else 'demo_alpha'
                    attack = page.evaluate('''async (other) => {
                        const response=await fetch('/api/demo/owners/'+other+'/series', {
                            headers: {'X-Owner-ID':other}});
                        return {status:response.status, text:await response.text()};
                    }''', other)
                    assert attack['status'] == 404 and forbidden_canary not in attack['text']
                    own_api = page.evaluate('''async () => {
                      const resp = await fetch('/api/demo/series'); return await resp.json();
                    }''')
                    assert own_api['owner_scope'] == owner
                    assert own_api['count'] == 3
                    assert own_api['mapping_approved'] is False
                    assert own_api['generation_contract'] == 'blocked_pending_review'
                    assert forbidden_canary not in json.dumps(own_api)
                    assert all(request.startswith(base+'/') for request in requests), requests
                    assert not errors, errors
                    screens[owner] = (ctx, page, own_api['snapshot_sha256'], errors, requests)

                ctx_a, page_a, before_a, _, _ = screens['demo_alpha']
                ctx_b, page_b, before_b, _, _ = screens['demo_beta']
                changed = copy.deepcopy([row for row in rows if row['workspace_key'] == 'demo_alpha'])
                changed[0]['invented_score'] = 666.125
                app.state.demo_owner_store.replace_owner_for_local_test('demo_alpha', changed)
                page_a.reload(wait_until='load')
                page_a.locator('#api-readout[data-connected="true"]').wait_for(timeout=10000)
                page_a.locator('#show-table').click()
                assert page_a.get_by_role('cell', name='666.125').count() == 1
                assert page_a.locator('#chart-view circle').count() == 3
                page_b.reload(wait_until='load')
                page_b.locator('#api-readout[data-connected="true"]').wait_for(timeout=10000)
                assert '666.125' not in page_b.content()
                new_a = page_a.evaluate("async ()=>(await (await fetch('/api/demo/series')).json()).snapshot_sha256")
                new_b = page_b.evaluate("async ()=>(await (await fetch('/api/demo/series')).json()).snapshot_sha256")
                assert new_a != before_a and new_b == before_b

                # An entirely new browser context has no legitimate test-driver session.
                outsider = browser.new_context()
                try:
                    page = outsider.new_page()
                    assert page.goto(base+'/api/demo/series').status == 401
                    assert page.goto(base+'/preview').status == 401
                    outsider.add_cookies([{'name':COOKIE, 'value':'forged-cookie',
                                           'url':base, 'httpOnly':True}])
                    assert page.goto(base+'/api/demo/series').status == 401
                finally:
                    outsider.close()
                for context, _, _, _, _ in screens.values():
                    context.close()
            finally:
                browser.close()
        return {'status':'PASS', 'engine':'Chromium', 'version':version,
                'transport':'real_loopback_http', 'storage':'one_shared_sqlite_in_memory',
                'synthetic_owners':2, 'rows_per_owner':3,
                'opaque_httponly_cookie_scope':'PASS',
                'cross_owner_direct_idor':'404/PASS',
                'header_spoof_cannot_impersonate':'PASS',
                'anonymous_and_forged_session':'401/PASS',
                'separate_owner_data_in_html_and_api':'PASS',
                'owner_a_mutation_not_reflected_in_owner_b':'PASS',
                'click_and_keyboard_chart_table':'PASS',
                'external_network_requests':0, 'page_javascript_errors':0,
                'real_customer_data':False, 'generation_authorized':False,
                'deployment_authorized':False,
                'generation_contract':'blocked_pending_review'}
    finally:
        server.should_exit = True
        runner.join(timeout=8)
        if runner.is_alive():
            raise RuntimeError('synthetic owner demo server did not shut down')


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--schema', type=Path, required=True)
    p.add_argument('--rows', type=Path, required=True)
    a = p.parse_args(argv)
    print(json.dumps(run(schema_path=a.schema, rows_path=a.rows), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
