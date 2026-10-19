"""Real Chromium HTTP E2E for synthetic client-rendered owner Chart/Table UI."""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
from pathlib import Path
import socket
import threading
import time

from playwright.async_api import async_playwright
import uvicorn

from astra_contracts.synthetic_owner_isolation import COOKIE, create_owner_like_app
from astra_contracts.synthetic_sqlite_dashboard import _digest


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


async def _fulfill(route, payload):
    await route.fulfill(
        status=200,
        content_type='application/json',
        body=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
    )


async def run(*, schema_path: Path, rows_path: Path, chromium: Path | None = None) -> dict:
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    schema['owner_ids'].append('demo_empty')
    rows = json.loads(rows_path.read_text(encoding='utf-8'))
    hostile = '<img src=x onerror=window.__astraXss=1>'
    next(row for row in rows if row['workspace_key'] == 'demo_alpha')['design_label'] = hostile
    app = create_owner_like_app(schema, rows, allow_empty_owner=True)
    tokens = {
        owner: app.state.demo_sessions.issue_for_local_test(owner)
        for owner in ('demo_alpha', 'demo_beta', 'demo_empty')
    }
    port = _port()
    base = f'http://127.0.0.1:{port}'
    server = uvicorn.Server(uvicorn.Config(
        app, host='127.0.0.1', port=port, log_level='error', access_log=False,
    ))
    runner = threading.Thread(target=server.run, daemon=True)
    runner.start()
    try:
        for _ in range(120):
            if server.started:
                break
            if not runner.is_alive():
                raise RuntimeError('client demo server exited during startup')
            time.sleep(.05)
        else:
            raise RuntimeError('client demo server startup timeout')

        async with async_playwright() as pw:
            options = {'headless': True}
            if chromium is not None:
                if not chromium.is_file():
                    raise ValueError('Chromium executable missing')
                options['executable_path'] = str(chromium)
            browser = await pw.chromium.launch(**options)
            version = browser.version
            contexts = []
            pages = []
            try:
                async def open_owner(owner: str, width: int, height: int = 820):
                    context = await browser.new_context(viewport={'width': width, 'height': height})
                    contexts.append(context)
                    await context.add_cookies([{
                        'name': COOKIE, 'value': tokens[owner], 'url': base,
                        'httpOnly': True, 'sameSite': 'Strict',
                    }])
                    page = await context.new_page()
                    pages.append(page)
                    log = {'errors': [], 'console': [], 'requests': [], 'http_errors': [], 'failures': []}
                    page.on('pageerror', lambda e: log['errors'].append(str(e)))
                    page.on('console', lambda m: log['console'].append(m.text) if m.type == 'error' else None)
                    page.on('request', lambda r: log['requests'].append(r.url))
                    page.on('response', lambda r: log['http_errors'].append(
                        f'{r.status} {r.url}') if r.status >= 400 else None)
                    page.on('requestfailed', lambda r: log['failures'].append(
                        f'{r.url} {r.failure}'))
                    return context, page, log

                evidence = {}
                context_a, page_a, log_a = await open_owner('demo_alpha', 1366)
                response = await page_a.goto(base + '/client-preview', wait_until='load')
                assert response and response.status == 200
                shell = await response.text()
                assert 'ALPHA_CANARY' not in shell and 'BETA_CANARY' not in shell
                assert '<tbody id="table-body"></tbody>' in shell
                assert '<g id="chart-points"></g>' in shell
                assert 'astra-expected-owner" content="demo_alpha' in shell
                await page_a.locator('#client-status[data-state="success"]').wait_for(timeout=10000)
                assert await page_a.locator('#table-body tr').count() == 3
                assert await page_a.locator('#chart-points circle').count() == 3
                text_a = await page_a.locator('#table-body').inner_text()
                assert 'ALPHA_CANARY' in text_a and 'BETA_CANARY' not in text_a
                assert hostile in text_a
                assert await page_a.locator('#table-body img').count() == 0
                assert await page_a.evaluate('window.__astraXss === undefined')
                assert await page_a.evaluate('document.cookie') == ''
                await page_a.locator('#show-table').click()
                assert await page_a.locator('#table-view').is_visible()
                await page_a.locator('#show-chart').focus()
                await page_a.keyboard.press('Enter')
                assert await page_a.locator('#chart-view').is_visible()
                await page_a.locator('#show-table').focus()
                await page_a.keyboard.press('Space')
                assert await page_a.locator('#table-view').is_visible()
                await page_a.locator('#show-chart').focus()
                await page_a.keyboard.press('ArrowLeft')
                assert await page_a.locator('#show-table').get_attribute('aria-selected') == 'true'
                assert await page_a.evaluate('document.documentElement.scrollWidth <= innerWidth')
                evidence['alpha_rows_points_xss_keyboard'] = 'PASS'

                context_b, page_b, log_b = await open_owner('demo_beta', 390, 844)
                await page_b.goto(base + '/client-preview', wait_until='load')
                await page_b.locator('#client-status[data-state="success"]').wait_for(timeout=10000)
                text_b = await page_b.locator('#table-body').inner_text()
                assert await page_b.locator('#table-body tr').count() == 3
                assert 'BETA_CANARY' in text_b and 'ALPHA_CANARY' not in text_b
                assert await page_b.evaluate('document.documentElement.scrollWidth <= innerWidth')
                idor = await page_a.evaluate('''async () => {
                  const r = await fetch('/api/demo/owners/demo_beta/series', {
                    headers: {'X-Owner-ID':'demo_beta'}
                  });
                  return {status:r.status, body:await r.text()};
                }''')
                assert idor['status'] == 404 and 'BETA_CANARY' not in idor['body']
                evidence['beta_isolation_and_mobile'] = 'PASS'

                _, page_empty, log_empty = await open_owner('demo_empty', 320, 640)
                await page_empty.goto(base + '/client-preview', wait_until='load')
                await page_empty.locator('#client-status[data-state="empty"]').wait_for(timeout=10000)
                assert await page_empty.locator('#empty-state').is_visible()
                assert await page_empty.locator('#table-body tr').count() == 0
                assert await page_empty.locator('#chart-points circle').count() == 0
                assert await page_empty.evaluate('document.documentElement.scrollWidth <= innerWidth')
                evidence['empty_state_and_small_mobile'] = 'PASS'

                # A failed first fetch leaves no partial view; the local API then recovers.
                _, retry_page, log_retry = await open_owner('demo_alpha', 768)
                remaining = {'count': 1}

                async def fail_first(route):
                    if remaining['count']:
                        remaining['count'] -= 1
                        await route.abort()
                    else:
                        await route.continue_()

                await retry_page.route('**/api/demo/series', fail_first)
                await retry_page.goto(base + '/client-preview', wait_until='load')
                await retry_page.locator('#client-status[data-state="error"]').wait_for(timeout=10000)
                assert await retry_page.locator('#table-body tr').count() == 0
                await retry_page.unroute('**/api/demo/series', fail_first)
                await retry_page.locator('#retry-load').click()
                await retry_page.locator('#client-status[data-state="success"]').wait_for(timeout=10000)
                assert await retry_page.locator('#table-body tr').count() == 3
                evidence['network_retry_recovery'] = 'PASS'

                # Change both rows and the API's own digest: the HTML page snapshot
                # still detects tampering and renders neither chart nor table.
                api_a = await (await context_a.request.get(base + '/api/demo/series')).json()
                altered = copy.deepcopy(api_a)
                altered['rows'][0]['invented_score'] += 1000
                altered['snapshot_sha256'] = _digest(altered['rows'])
                _, tamper_page, log_tamper = await open_owner('demo_alpha', 1280)

                async def serve_tampered(route):
                    await _fulfill(route, altered)

                await tamper_page.route('**/api/demo/series', serve_tampered)
                await tamper_page.goto(base + '/client-preview', wait_until='load')
                await tamper_page.locator('#client-status[data-state="error"]').wait_for(timeout=10000)
                assert '무결성' in await tamper_page.locator('#client-status').inner_text()
                assert await tamper_page.locator('#table-body tr').count() == 0
                assert await tamper_page.locator('#chart-points circle').count() == 0
                evidence['modified_api_response_blocked'] = 'PASS'

                api_b = await (await context_b.request.get(base + '/api/demo/owners/demo_beta/series')).json()
                _, mismatch_page, log_mismatch = await open_owner('demo_alpha', 1280)

                async def serve_other_owner(route):
                    await _fulfill(route, api_b)

                await mismatch_page.route('**/api/demo/series', serve_other_owner)
                await mismatch_page.goto(base + '/client-preview', wait_until='load')
                await mismatch_page.locator('#client-status[data-state="error"]').wait_for(timeout=10000)
                assert '소유자 정보' in await mismatch_page.locator('#client-status').inner_text()
                assert await mismatch_page.locator('#table-body tr').count() == 0
                evidence['different_owner_response_blocked'] = 'PASS'

                # Start a valid A request, then a newer B request. The delayed A
                # response arrives last and must not replace the newer error state.
                _, stale_page, log_stale = await open_owner('demo_alpha', 1280)
                await stale_page.goto(base + '/client-preview', wait_until='load')
                await stale_page.locator('#client-status[data-state="success"]').wait_for(timeout=10000)
                first_started = asyncio.Event()
                sequence = {'count': 0}

                async def delayed_old_response(route):
                    sequence['count'] += 1
                    if sequence['count'] == 1:
                        first_started.set()
                        await asyncio.sleep(.7)
                        await _fulfill(route, api_a)
                    elif sequence['count'] == 2:
                        await _fulfill(route, api_b)
                    else:
                        await route.continue_()

                await stale_page.route('**/api/demo/series', delayed_old_response)
                await stale_page.locator('#retry-load').click()
                await first_started.wait()
                await asyncio.sleep(.24)
                await stale_page.context.add_cookies([{
                    'name': COOKIE, 'value': tokens['demo_beta'], 'url': base,
                    'httpOnly': True, 'sameSite': 'Strict',
                }])
                await stale_page.locator('#retry-load').click()
                await stale_page.locator('#client-status[data-state="error"]').wait_for(timeout=10000)
                assert '소유자 정보' in await stale_page.locator('#client-status').inner_text()
                await asyncio.sleep(.6)
                assert '소유자 정보' in await stale_page.locator('#client-status').inner_text()
                assert await stale_page.locator('#table-body tr').count() == 0
                assert await stale_page.locator('#chart-points circle').count() == 0
                assert sequence['count'] == 2
                evidence['late_old_owner_response_ignored'] = 'PASS'

                # Same-turn repeated activation is coalesced into one API fetch.
                await stale_page.unroute('**/api/demo/series', delayed_old_response)
                await stale_page.context.add_cookies([{
                    'name': COOKIE, 'value': tokens['demo_alpha'], 'url': base,
                    'httpOnly': True, 'sameSite': 'Strict',
                }])
                calls_before_double_click = sum('/api/demo/series' in url for url in log_stale['requests'])
                await stale_page.locator('#retry-load').evaluate('(button) => { button.click(); button.click(); }')
                await stale_page.locator('#client-status[data-state="success"]').wait_for(timeout=10000)
                assert await stale_page.locator('#table-body tr').count() == 3
                calls_after_double_click = sum('/api/demo/series' in url for url in log_stale['requests'])
                assert calls_after_double_click - calls_before_double_click == 1
                evidence['rapid_duplicate_fetch_coalesced'] = 'PASS'

                logs = [log_a, log_b, log_empty, log_retry, log_tamper, log_mismatch, log_stale]
                errors = [item for log in logs for item in log['errors']]
                console_errors = [item for log in logs for item in log['console']]
                requests = [item for log in logs for item in log['requests']]
                http_errors = [item for log in logs for item in log['http_errors']]
                failures = [item for log in logs for item in log['failures']]
                assert not errors, errors
                assert len(http_errors) == 1, http_errors
                assert len(failures) == 1, failures
                assert all('/api/demo/owners/demo_beta/series' in item and item.startswith('404 ')
                           for item in http_errors), http_errors
                assert all('/api/demo/series' in item for item in failures), failures
                assert all('404' in item or 'ERR_FAILED' in item for item in console_errors), console_errors
                assert all(url.startswith(base + '/') for url in requests), requests
                assert any(url.endswith('/client-assets/owner-client-chart-table.js') for url in requests)
                evidence.update({
                    'javascript_errors': 0,
                    'unexpected_console_errors': 0,
                    'expected_http_errors': http_errors,
                    'expected_network_failures': len(failures),
                    'external_requests': 0,
                    'browser': 'Chromium ' + version,
                    'transport': 'real_loopback_http',
                    'database': 'shared_synthetic_sqlite_in_memory',
                    'generation_contract': 'blocked_pending_review',
                    'generation_authorized': False,
                    'deployment_authorized': False,
                })
            finally:
                for context in contexts:
                    await context.close()
                await browser.close()
        return {'status': 'PASS', **evidence}
    finally:
        server.should_exit = True
        runner.join(timeout=8)
        if runner.is_alive():
            raise RuntimeError('synthetic client demo server did not shut down')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--chromium', type=Path)
    args = parser.parse_args(argv)
    result = asyncio.run(run(schema_path=args.schema, rows_path=args.rows, chromium=args.chromium))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
