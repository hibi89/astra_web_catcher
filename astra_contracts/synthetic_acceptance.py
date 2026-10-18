"""One-unit ASTRA synthetic-only acceptance checks of a generated preview.

Reads ONLY an ASTRA-created, empty-temp-root preview with fixed trusted code.
Executes ASGI endpoints in-process using an independent temporary SQLite DB.
Never visits the original website, deploys, grants approval, or writes client data.

Run: python -m astra_contracts.synthetic_acceptance /tmp/astra-synth-...
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Literal

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, ValidationError

from astra_contracts.generation_contract import fingerprint
from astra_contracts.synthetic_bridge import SyntheticBridgeTrace, synthetic_route
from astra_contracts.synthetic_generator import APP, HTML, SyntheticDemo
from astra_contracts.observation import Feature


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SyntheticAcceptanceReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['synthetic_only_passed'] = 'synthetic_only_passed'
    original_behavior_verified: Literal[False] = False
    production_ready: Literal[False] = False
    user_database_accessed: Literal[False] = False
    original_generation_approved: Literal[False] = False
    synthetic_fixture_sha256: str
    features_exercised: list[str]
    observed_trace_ids_checked: list[str]
    unverified_observation_ids: list[str]
    checks: list[str]


def _safe_file(root: Path, relative: str) -> Path:
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'symlink in generated preview: {relative}')
    if not path.is_file():
        raise ValueError(f'required preview file absent: {relative}')
    return path


def check_generated_preview(root: Path) -> SyntheticAcceptanceReport:
    """Accept only known generated templates and synthetic metadata; fail closed."""
    base = Path(root)
    temp = Path(tempfile.gettempdir()).resolve()
    if (base.is_symlink() or not base.is_dir() or
        base.parent.resolve() != temp or not base.name.startswith('astra-synth-') or
        base.resolve().parent != temp):
        raise ValueError('only a direct, non-symlinked astra-synth-* system-temp preview is accepted')

    app_file = _safe_file(base, 'app/main.py')
    html_file = _safe_file(base, 'app/index.html')
    seed_file = _safe_file(base, 'data/seed.json')
    trace_file = _safe_file(base, 'data/astra_preview_trace.json')
    if app_file.read_text(encoding='utf-8') != APP or html_file.read_text(encoding='utf-8') != HTML:
        raise ValueError('preview source differs from trusted fixed synthetic template')

    demo = SyntheticDemo.model_validate_json(seed_file.read_text(encoding='utf-8'))
    trace = SyntheticBridgeTrace.model_validate_json(trace_file.read_text(encoding='utf-8'))
    if (trace.source_schema_kind != 'synthetic_fixture' or
        trace.synthetic_fixture_sha256 != fingerprint(demo) or
        trace.preflight_status != 'blocked_pending_review' or
        not trace.preflight_block_reasons or
        'independent_generation_not_authorized' not in trace.preflight_block_reasons):
        raise ValueError('synthetic trace identity or blocked preflight does not match')

    for t in trace.trace:
        correct = synthetic_route(t.feature, demo)
        if t.result == 'synthetic_smoke_only':
            if correct is None or t.example_route != correct:
                raise ValueError('feature trace points to nonexistent or mismatched synthetic route')
        elif t.result == 'not_simulated' and t.example_route is not None:
            raise ValueError('unsupported feature contains misleading example route')

    # Dynamic load is only allowed AFTER byte-exact fixed-template comparison.
    spec = importlib.util.spec_from_file_location('_astra_checked_synthetic_demo', app_file)
    if spec is None or spec.loader is None:
        raise ValueError('cannot inspect generated preview module')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    checks: list[str] = []
    with tempfile.TemporaryDirectory(prefix='astra-accept-') as d:
        db = Path(d) / 'acceptance.sqlite3'
        app = module.create_app(db)
        with TestClient(app) as client:
            def expect(condition: bool, label: str) -> None:
                if not condition:
                    raise ValueError(f'synthetic acceptance failed: {label}')
                checks.append(label)

            health = client.get('/health')
            expect(health.status_code == 200 and health.json() == {'status': 'ok', 'synthetic': True}, 'synthetic_health')
            home = client.get('/')
            expect(home.status_code == 200 and 'SYNTHETIC TEST DATA ONLY' in home.text, 'synthetic_html')
            all_items = client.get('/api/items')
            fixture_rows = [row.model_dump() for row in demo.items]
            sorted_rows = sorted(fixture_rows, key=lambda x: (-x['score'], x['id']))
            expect(all_items.status_code == 200 and all_items.json() == {'synthetic': True, 'items': sorted_rows}, 'synthetic_list_exact')

            example = demo.items[0]
            expected_cat = [x for x in sorted_rows if x['category'] == example.category]
            cat = client.get('/api/items', params={'category': example.category})
            expect(cat.status_code == 200 and cat.json()['items'] == expected_cat, 'synthetic_category_filter_exact')
            query = client.get('/api/items', params={'q': example.title})
            expect(query.status_code == 200 and any(x['id'] == example.id for x in query.json()['items']), 'synthetic_search_exact')
            detail = client.get('/api/items/' + example.id)
            expect(detail.status_code == 200 and detail.json() == example.model_dump(), 'synthetic_detail_exact')
            expect(client.get('/api/items/does-not-exist').status_code == 404, 'synthetic_missing_detail_404')
            expect(client.get('/api/items', params={'limit': 0}).status_code == 422, 'synthetic_limit_validation')
            # Search wildcards must not silently enumerate all seeded rows.
            for token in ('%', '_'):
                wildcard = client.get('/api/items', params={'q': token})
                expect(wildcard.status_code == 200 and wildcard.json()['items'] == [x for x in sorted_rows if token in x['title']], 'synthetic_search_escape_' + ('percent' if token == '%' else 'underscore'))
            for entry in trace.trace:
                if entry.result == 'synthetic_smoke_only':
                    response = client.get(entry.example_route)
                    expect(response.status_code == 200 and bool(response.json().get('items', [response.json()])), 'trace_route_' + entry.observation_id)

        # Use a SECOND instance on the same disposable test DB; data must survive.
        with TestClient(module.create_app(db)) as again:
            expect(again.get('/api/items').json()['items'] == sorted_rows, 'synthetic_sqlite_restart_persistence')

    return SyntheticAcceptanceReport(
        synthetic_fixture_sha256=fingerprint(demo),
        features_exercised=['list', 'filter', 'search', 'detail'],
        observed_trace_ids_checked=sorted(x.observation_id for x in trace.trace if x.result == 'synthetic_smoke_only'),
        unverified_observation_ids=sorted(set(trace.unresolved_observation_ids)),
        checks=checks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Synthetic-only, in-process acceptance of fixed generated FastAPI preview')
    parser.add_argument('generated_temp_folder', type=Path)
    args = parser.parse_args(argv)
    try:
        report = check_generated_preview(args.generated_temp_folder)
    except (ValueError, ValidationError, OSError, UnicodeError, ImportError, RuntimeError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
