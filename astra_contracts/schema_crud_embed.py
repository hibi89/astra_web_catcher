"""Opt-in fictional CRUD sandbox inside an *already generated* ASTRA preview.

Never changes the protected generated app, source-site evidence, or owner DB.
Unlike a production auth layer, this deliberately refuses all real data and
requires explicit opt-in; run only on loopback with disposable fixtures.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from astra_contracts.generation_contract import fingerprint
from astra_contracts.schema_query_embed import (
    EXTENDED_SOURCE, EmbeddedQueryReport, _safe_root,
)
from astra_contracts.schema_query_extension import QueryPlan, verify_query_plan
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable
from astra_contracts.synthetic_acceptance import check_generated_preview
from astra_contracts.synthetic_generator import APP, HTML

# The source of the demo CRUD runtime must be this independently reviewed,
# fixed module; NEVER interpolate observed-site/user-provided executable code.
CRUD_SOURCE = Path(__file__).with_name('synthetic_crud.py').read_text(encoding='utf-8')

FULL_SOURCE = '''"""ASTRA generated fictional-only preview with OPT-IN disposable CRUD.

Only launch on 127.0.0.1. No user DB. No credentials. Not production-ready.
"""
import os
import tempfile
from pathlib import Path
from app.extended import create_extended_app
from app.sandbox_crud import create_app as create_sandbox_crud


def create_full_app(base_db_path=None, *, enable_synthetic_crud=False):
    app = create_extended_app(base_db_path)
    if enable_synthetic_crud:
        # The isolated SQLite fixture is NEVER the main preview's SQLite file.
        sandbox = tempfile.TemporaryDirectory(prefix='astra-synth-crud-')
        try:
            isolated = create_sandbox_crud(Path(sandbox.name) / 'fiction.sqlite3')
            app.mount('/sandbox', isolated)
            # Hold the temp-directory alive as long as the ASGI app object lives.
            app.state.synthetic_crud_tempdir = sandbox
        except Exception:
            sandbox.cleanup()
            raise
    return app


# No CRUD endpoint without an exact opt-in. Never set this in production.
app = create_full_app(enable_synthetic_crud=(
    os.environ.get('ASTRA_ENABLE_SYNTHETIC_CRUD') == 'YES_TEMP_ONLY'))
'''

GENERATED_TEST = '''"""Actual generated project's opt-in/off CRUD isolation tests."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.full import create_full_app


def test_sandbox_is_disabled_by_default(tmp_path):
    app = create_full_app(tmp_path / 'base.sqlite3')
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/api/rows', params={'sort_by': '__UNKNOWN_FIELD__'}).status_code == 422
        assert client.get('/sandbox/api/items').status_code == 404
        assert client.post('/api/items', json={}).status_code == 405


def test_disposable_sandbox_full_crud(tmp_path):
    app = create_full_app(tmp_path / 'base.sqlite3', enable_synthetic_crud=True)
    sandbox_dir = Path(app.state.synthetic_crud_tempdir.name)
    item = {'id':'test1','title':'fictional','category':'demo','score':3}
    with TestClient(app) as client:
        assert client.post('/sandbox/api/items', json=item).status_code == 201
        assert client.get('/sandbox/api/items/test1').json() == item
        assert client.patch('/sandbox/api/items/test1', json={'score':7}).json()['score'] == 7
        assert client.post('/sandbox/api/items', json=item).status_code == 409
        assert client.post('/sandbox/api/items', json={**item,'score':True}).status_code == 422
        assert client.delete('/sandbox/api/items/test1').status_code == 204
        assert client.get('/sandbox/api/items/test1').status_code == 404
        assert client.get('/health').json() == {'status':'ok','synthetic':True}
        assert client.get('/api/items').status_code == 200
        assert client.post('/api/items', json=item).status_code == 405
    app.state.synthetic_crud_tempdir.cleanup()
    assert not sandbox_dir.exists()
'''

README = '''# ASTRA optional synthetic CRUD for GENERATED preview only

* No customer database, source-site modification, copied private code, or production approval.
* Immutable app/main.py and app/index.html; existing app.extended:app works unchanged.
* Standard: `python -m uvicorn app.full:app --host 127.0.0.1 --port 8017` has NO CRUD.
* Explicit sandbox only: `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY python -m uvicorn app.full:app --host 127.0.0.1 --port 8017`.
* CRUD only at `/sandbox/api/items`, using a separate disposable new SQLite file in
  the OS temp root; existing read-only `/api/items` and `/api/rows` stay separate.
* Test: `python -m pytest -q tests/test_embedded_crud.py`.
* Do NOT deploy or expose this unauthenticated sandbox externally. In particular,
  never use `--host 0.0.0.0` or connect real data. No production permission granted.
'''


class CRUDEmbedReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal['0.1'] = '0.1'
    status: Literal['synthetic_crud_opt_in_integrated_passed'] = 'synthetic_crud_opt_in_integrated_passed'
    prior_query_extension_verified: Literal[True] = True
    write_routes_off_by_default: Literal[True] = True
    disposable_sqlite_only: Literal[True] = True
    original_template_unchanged: Literal[True] = True
    original_site_behavior_verified: Literal[False] = False
    customer_database_connected: Literal[False] = False
    deployment_authorized: Literal[False] = False
    generated_crud_sha256: str
    source_query_plan_sha256: str


def _preview_guards(root: Path) -> tuple[AlternateSyntheticTable, QueryPlan]:
    root = _safe_root(root)
    base = check_generated_preview(root)
    names = ('app/extended.py','data/query_physical_fixture.json',
             'data/query_cases.json','data/query_embed_report.json')
    for n in names:
        p = root / n
        if p.is_symlink() or not p.is_file():
            raise ValueError('required trusted read-only query extension absent or symlinked')
    table_bytes = (root / names[1]).read_bytes()
    table = AlternateSyntheticTable.model_validate_json(table_bytes)
    plan = QueryPlan.model_validate_json((root / names[2]).read_bytes())
    verify_query_plan(table, plan)
    generated_source = EXTENDED_SOURCE.replace('__FIXTURE_SHA256__', hashlib.sha256(table_bytes).hexdigest())
    if (root / names[0]).read_text(encoding='utf-8') != generated_source:
        raise ValueError('read-only extension does not match trusted generated template')
    report = EmbeddedQueryReport.model_validate_json((root / names[3]).read_bytes())
    if (report.physical_table_sha256 != fingerprint(table)
            or report.query_cases_sha256 != fingerprint(plan)
            or report.base_preview_sha256 != fingerprint(base)):
        raise ValueError('query extension report is missing or inconsistent')
    if ((root / 'app/main.py').read_text(encoding='utf-8') != APP or
            (root / 'app/index.html').read_text(encoding='utf-8') != HTML):
        raise ValueError('protected template changed')
    return table, plan


def embed_synthetic_crud(root: Path) -> CRUDEmbedReport:
    """Append trusted optional CRUD files; never overwrite prior files."""
    root = _safe_root(Path(root))
    _, plan = _preview_guards(root)
    files = {
        'app/full.py': FULL_SOURCE,
        'app/sandbox_crud.py': CRUD_SOURCE,
        'tests/test_embedded_crud.py': GENERATED_TEST,
        'README_CRUD.md': README,
    }
    report_rel = 'data/crud_embed_report.json'
    for relative in [*files, report_rel]:
        path = root / relative
        if path.is_symlink() or path.exists():
            raise ValueError('existing CRUD output cannot be overwritten')
    for relative, contents in files.items():
        with (root / relative).open('x', encoding='utf-8') as handle:
            handle.write(contents)
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', 'tests/test_embedded_crud.py'],
        cwd=root, capture_output=True, text=True, timeout=35,
    )
    if result.returncode:
        raise ValueError('generated CRUD self-tests failed: ' + result.stdout[-900:] + result.stderr[-400:])
    report = CRUDEmbedReport(generated_crud_sha256=hashlib.sha256(CRUD_SOURCE.encode()).hexdigest(),
                             source_query_plan_sha256=fingerprint(plan))
    with (root / report_rel).open('x', encoding='utf-8') as handle:
        handle.write(report.model_dump_json(indent=2) + '\n')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Add optional disposable CRUD to a verified generated synthetic preview')
    parser.add_argument('existing_generated_temp_preview', type=Path)
    args = parser.parse_args(argv)
    try:
        report = embed_synthetic_crud(args.existing_generated_temp_preview)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
