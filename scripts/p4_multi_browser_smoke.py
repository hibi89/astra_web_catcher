"""Cross-engine offline browser smoke for the synthetic ASTRA chart/table preview.

Optionally verifies pinned public observation provenance; always uses fabricated data.
No owner DB, server, external URL or deployment is accessed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from astra_contracts.synthetic_chart_table_preview import render_preview

VIEWPORTS = (
    ('desktop', 1366, 768),
    ('mobile', 390, 844),
    ('small_mobile', 320, 640),
)
ENGINES = ('chromium', 'firefox', 'webkit', 'msedge')


def run(*, schema_path: Path, rows_path: Path, archive: Path | None,
        engines: tuple[str, ...], chromium_path: Path | None = None) -> dict:
    if not engines or len(set(engines)) != len(engines) or any(e not in ENGINES for e in engines):
        raise ValueError('Specify distinct supported engines')
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    rows = json.loads(rows_path.read_text(encoding='utf-8'))
    html = render_preview(schema, rows, archive=archive)
    payload = '<img src=x onerror="window.__ASTRA_XSS__=true">'
    entity_key = schema['proposed_bindings']['entity_identifier']
    malicious_rows = [dict(row) for row in rows]
    malicious_rows[0][entity_key] = payload
    hostile_html = render_preview(schema, malicious_rows, archive=archive)
    results = []

    with sync_playwright() as playwright:
        for engine in engines:
            typ = playwright.chromium if engine in ('chromium', 'msedge') else getattr(playwright, engine)
            opts = {'headless': True}
            if engine == 'msedge':
                opts['channel'] = 'msedge'
            elif engine == 'chromium' and chromium_path is not None:
                if not chromium_path.is_file():
                    raise ValueError('Explicit Chromium binary does not exist')
                opts['executable_path'] = str(chromium_path)
            browser = typ.launch(**opts)
            version = browser.version
            try:
                for label, width, height in VIEWPORTS:
                    context = browser.new_context(viewport={'width': width, 'height': height},
                                                  reduced_motion='reduce')
                    try:
                        page = context.new_page()
                        errors, requests = [], []
                        page.on('pageerror', lambda exc: errors.append(str(exc)))
                        page.on('request', lambda req: requests.append(req.url))
                        page.set_content(html, wait_until='load')
                        assert page.locator('#chart-view svg').is_visible(), (engine, label, 'chart')
                        assert page.locator('#chart-view circle').count() == len(rows), (engine, label, 'points')
                        assert page.locator('#table-view').is_hidden(), (engine, label, 'initially hidden')
                        assert page.locator('table tbody tr').count() == len(rows), (engine, label, 'rows')
                        page.locator('#show-table').click()
                        assert page.locator('#table-view').is_visible(), (engine, label, 'table click')
                        assert page.locator('#chart-view').is_hidden(), (engine, label, 'hide chart')
                        assert page.locator('#show-table').get_attribute('aria-pressed') == 'true'
                        page.locator('#show-chart').focus()
                        page.keyboard.press('Enter')
                        assert page.locator('#chart-view svg').is_visible(), (engine, label, 'chart Enter')
                        assert page.locator('#table-view').is_hidden(), (engine, label, 'table hidden')
                        page.locator('#show-table').focus()
                        page.keyboard.press('Space')
                        assert page.locator('#table-view').is_visible(), (engine, label, 'table Space')
                        assert page.locator('#chart-view').is_hidden(), (engine, label, 'chart hidden')
                        assert page.locator('table tbody tr').count() == len(rows), (engine, label, 'row retention')
                        assert page.locator('#table-view').evaluate('(el) => getComputedStyle(el).overflowX') == 'auto'
                        assert not errors, (engine, label, 'page errors', errors)
                        assert not requests, (engine, label, 'requests', requests)
                        results.append({'engine': engine, 'version': version, 'viewport': label,
                                        'rows': len(rows), 'status': 'PASS', 'requests': 0, 'pageerrors': 0})
                    finally:
                        context.close()
                test_context = browser.new_context()
                try:
                    page = test_context.new_page()
                    page.set_content(hostile_html, wait_until='load')
                    assert page.evaluate('window.__ASTRA_XSS__ === undefined'), (engine, 'XSS executed')
                    assert page.locator('img').count() == 0, (engine, 'injection became DOM element')
                    assert page.locator('table tbody tr').count() == len(rows)
                    results.append({'engine': engine, 'version': version,
                                    'viewport': 'injection_probe', 'status': 'PASS'})
                finally:
                    test_context.close()
            finally:
                browser.close()
    return {'status': 'PASS', 'engines_tested': list(engines), 'cases': results,
            'preview_data_kind': 'synthetic_fixture', 'render_mode': 'page.set_content',
            'pinned_archive_verified': archive is not None,
            'windows_edge_tested': 'msedge' in engines,
            'original_source_semantics_verified': False,
            'owner_schema_approved': False, 'generation_contract': 'blocked_pending_review'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--rows', required=True, type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--engine', action='append', choices=ENGINES, required=True)
    parser.add_argument('--chromium-path', type=Path)
    args = parser.parse_args(argv)
    output = run(schema_path=args.fixture, rows_path=args.rows, archive=args.archive,
                 engines=tuple(args.engine), chromium_path=args.chromium_path)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
