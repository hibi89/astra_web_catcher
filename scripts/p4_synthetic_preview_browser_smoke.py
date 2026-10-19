"""Offline deterministic Chromium UX smoke for ASTRA's synthetic Chart/Table preview.

Only generated synthetic rows. Does not access owner data or authorize generation.
Requires playwright Python and an explicitly installed Chromium executable.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from astra_contracts.synthetic_chart_table_preview import render_preview

VIEWPORTS = (("desktop", 1366, 768), ("laptop", 1280, 720),
             ("tablet", 768, 1024), ("mobile", 390, 844),
             ("small_mobile", 320, 640))


def run(*, chromium: Path, fixture: Path, rows: Path, archive: Path) -> dict:
    if not chromium.is_file():
        raise ValueError('Chromium executable unavailable; cannot claim browser pass')
    schema = json.loads(fixture.read_text(encoding='utf-8'))
    data = json.loads(rows.read_text(encoding='utf-8'))
    html = render_preview(schema, data, archive=archive)
    cases = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=str(chromium), headless=True,
                                     args=['--disable-dev-shm-usage'])
        try:
            for name, width, height in VIEWPORTS:
                context = browser.new_context(viewport={'width': width, 'height': height},
                                              reduced_motion='reduce', java_script_enabled=True)
                page = context.new_page()
                errors, network = [], []
                page.on('pageerror', lambda err: errors.append(str(err)))
                page.on('request', lambda req: network.append(req.url))
                page.set_content(html, wait_until='load')
                assert page.locator('main').is_visible()
                assert page.locator('#chart-view svg').is_visible()
                assert page.locator('#chart-view circle').count() == len(data)
                assert page.locator('#table-view').is_hidden()
                assert page.locator('table tbody tr').count() == len(data)
                assert page.locator('#show-chart').get_attribute('aria-pressed') == 'true'
                assert page.locator('#show-table').get_attribute('aria-pressed') == 'false'
                # A click switches to the same data represented as a table.
                page.get_by_role('button', name='Table').click()
                assert page.locator('#table-view').is_visible()
                assert page.locator('#chart-view').is_hidden()
                assert page.locator('#show-chart').get_attribute('aria-pressed') == 'false'
                assert page.locator('#show-table').get_attribute('aria-pressed') == 'true'
                assert page.locator('table tbody tr').count() == len(data)
                # Keyboard controls also work (Enter / Space).
                page.locator('#show-chart').focus()
                page.keyboard.press('Enter')
                assert page.locator('#chart-view svg').is_visible()
                assert page.locator('#table-view').is_hidden()
                page.locator('#show-table').focus()
                page.keyboard.press('Space')
                assert page.locator('#table-view').is_visible()
                assert page.locator('#chart-view').is_hidden()
                # Declared min width is intentionally contained in horizontally scrollable view.
                assert page.locator('#table-view').evaluate('(el) => getComputedStyle(el).overflowX') == 'auto'
                assert not errors, f'{name} JavaScript errors: {errors}'
                assert not network, f'{name} unexpected network requests: {network}'
                cases.append({'viewport': name, 'width': width, 'height': height,
                              'rows': len(data), 'network_requests': 0, 'js_errors': 0,
                              'click_and_keyboard_switch': 'PASS'})
                context.close()
            # HTML escaping is tested in an actual running JS engine.
            malicious = [dict(row) for row in data]
            first_id = schema['proposed_bindings']['entity_identifier']
            target = malicious[0][first_id]
            payload = '<img src=x onerror="window.__ASTRA_XSS__=true">'
            malicious[0][first_id] = payload
            # Prevent collision with an existing entity/time combination.
            assert payload != target
            injection = render_preview(schema, malicious)
            page = browser.new_page()
            page.set_content(injection, wait_until='load')
            assert page.evaluate('window.__ASTRA_XSS__ === undefined')
            assert page.locator('img').count() == 0
            assert page.locator('table tbody tr').count() == len(data)
            page.close()
        finally:
            browser.close()
        version = browser.version
    return {'engine': 'Chromium', 'version': version,
            'rendering': 'Playwright page.set_content, no file URL navigation',
            'total_viewports': len(cases), 'all': 'PASS', 'injection_test': 'PASS', 'cases': cases,
            'windows_edge_tested': False, 'firefox_tested': False, 'webkit_tested': False}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--chromium', required=True, type=Path)
    p.add_argument('--fixture', required=True, type=Path)
    p.add_argument('--rows', required=True, type=Path)
    p.add_argument('--archive', required=True, type=Path)
    args = p.parse_args(argv)
    result = run(chromium=args.chromium, fixture=args.fixture, rows=args.rows, archive=args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
