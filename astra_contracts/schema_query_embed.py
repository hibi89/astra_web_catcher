"""Embed a fixed, read-only physical-field query route in a GENERATED fictional preview.

Never changes `app/main.py`, the original synthetic template, or any real DB.
The new launch entrypoint is `app.extended:app`, in the same isolated preview.
Input is an explicitly declared synthetic table + independently authored query plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.generation_contract import GenerationRequest, fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_query_extension import QueryPlan, verify_query_plan
from astra_contracts.schema_reuse_adapter import (
    AlternateSyntheticTable, SchemaAcceptanceCases, normalize_table, run_schema_reuse,
)
from astra_contracts.synthetic_acceptance import check_generated_preview
from astra_contracts.synthetic_generator import APP, HTML


# A complete, fixed query engine. Only the 64-character SHA of a *fictional fixture*
# is interpolated into this trusted template, never a user's prose or site source.
EXTENDED_SOURCE = '''"""ASTRA generated extended SYNTHETIC-ONLY app. NO owner DB, NO permission grants."""
import hashlib
import json
import re
from pathlib import Path
from fastapi import HTTPException, Query
from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_SHA256 = "__FIXTURE_SHA256__"
INTEGER = re.compile(r"^(0|[1-9][0-9]{0,4})$")


def create_extended_app(database_path=None):
    base = create_app(database_path)
    path = ROOT / "data" / "query_physical_fixture.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symlinked synthetic query fixture")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != FIXTURE_SHA256:
        raise ValueError("synthetic query fixture was changed")
    table = json.loads(payload)
    if (table.get("source_kind") != "synthetic_fixture" or
            table.get("run_mode") != "temporary_demo_only" or
            table.get("original_site_behavior_verified") is not False or
            table.get("customer_database_connected") is not False or
            table.get("schema_mapping_approved") is not False):
        raise ValueError("synthetic-only markers missing")
    physical = {x["source_field"]: x["logical_field"] for x in table["bindings"]}
    logical = {v: k for k, v in physical.items()}
    if (len(physical) != 4 or set(logical) != {"id", "title", "category", "score"}):
        raise ValueError("unexpected fixture bindings")
    id_key = logical["id"]
    rows = table["rows"]
    if not isinstance(rows, list) or not rows or any(set(row) != set(physical) for row in rows):
        raise ValueError("unexpected fixture rows")

    @base.get("/api/rows")
    def typed_query(sort_by: str, direction: str = "asc", filter_by: str | None = None,
                    filter_value: str | None = None, limit: int = Query(100, ge=1, le=100)):
        if sort_by not in physical or direction not in ("asc", "desc"):
            raise HTTPException(422, "unrecognized sort field or direction")
        if (filter_by is None) != (filter_value is None):
            raise HTTPException(422, "filter field/value must be paired")
        chosen = [dict(row) for row in rows]
        if filter_by is not None:
            if filter_by not in physical:
                raise HTTPException(422, "unrecognized filter field")
            if physical[filter_by] == "score":
                if not INTEGER.fullmatch(filter_value) or int(filter_value) > 10000:
                    raise HTTPException(422, "invalid integer filter")
                expected = int(filter_value)
            else:
                expected = filter_value
            chosen = [r for r in chosen if type(r[filter_by]) is type(expected) and r[filter_by] == expected]
        chosen.sort(key=lambda row: row[id_key])
        chosen.sort(key=lambda row: row[sort_by].casefold()
                    if isinstance(row[sort_by], str) else row[sort_by],
                    reverse=direction == "desc")
        return {"synthetic": True, "source_kind": "synthetic_fixture",
                "table_name": table["table_name"], "items": chosen[:limit],
                "original_site_behavior_verified": False}

    return base


app = create_extended_app()
'''

GENERATED_TEST = '''"""Acceptance of the actual GENERATED extended FastAPI application, not source site."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.extended import create_extended_app

ROOT = Path(__file__).resolve().parents[1]


def test_embedded_physical_queries(tmp_path):
    cases = json.loads((ROOT / "data" / "query_cases.json").read_text(encoding="utf-8"))
    table = json.loads((ROOT / "data" / "query_physical_fixture.json").read_text(encoding="utf-8"))
    id_field = next(x["source_field"] for x in table["bindings"] if x["logical_field"] == "id")
    with TestClient(create_extended_app(tmp_path / "embedded_test.sqlite3")) as client:
        assert client.get("/health").json() == {"status": "ok", "synthetic": True}
        assert client.get("/").status_code == 200
        assert client.get("/api/items").status_code == 200
        for case in cases["cases"]:
            params = {k: case[k] for k in ("sort_by", "direction", "limit")}
            if case["filter_by"] is not None:
                params.update(filter_by=case["filter_by"], filter_value=case["filter_value"])
            response = client.get("/api/rows", params=params)
            assert response.status_code == 200, (case["id"], response.text)
            payload = response.json()
            assert payload["synthetic"] is True
            assert payload["original_site_behavior_verified"] is False
            assert [row[id_field] for row in payload["items"]] == case["expected_ids"]
        for wrong in (
            {"sort_by": "__class__"},
            {"sort_by": id_field, "filter_by": "undeclared", "filter_value": "x"},
            {"sort_by": id_field, "limit": 0},
            {"sort_by": id_field, "direction": "DROP TABLE"},
        ):
            assert client.get("/api/rows", params=wrong).status_code == 422
        assert client.get("/api/items/nonexistent").status_code == 404
'''

README_EXTENDED = '''# ASTRA generated fictional-only query extension

Runs **inside the generated preview project**, using an optional entrypoint:

```sh
python -m uvicorn app.extended:app --host 127.0.0.1 --port 8017
python -m pytest -q tests/test_embedded_query.py
```

`/api/rows?sort_by=<bound_physical_field>&direction=desc&filter_by=<bound_physical_field>&filter_value=<value>`
works for the FOUR columns explicitly declared in the synthetic JSON fixture.
Original `/`, `/health`, `/api/items`, `/api/items/{id}` remain unchanged.

This adds no real DB adapters, production credentials, mutations, or proof of an
observed website. `app/main.py` is byte-identical to the protected demo template.
Do not deploy this preview.
'''


class EmbeddedQueryReport(BaseModel):
    model_config = ConfigDict(extra='forbid')

    version: Literal['0.1'] = '0.1'
    status: Literal['generated_synthetic_query_integrated_passed'] = 'generated_synthetic_query_integrated_passed'
    physical_table_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    query_cases_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    base_preview_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    accepted_cases: int = Field(ge=2)
    generated_entrypoint: Literal['app.extended:app'] = 'app.extended:app'
    original_app_source_unchanged: Literal[True] = True
    original_site_behavior_verified: Literal[False] = False
    customer_database_accessed: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def _safe_root(root: Path) -> Path:
    tmp = Path(tempfile.gettempdir()).resolve()
    if (root.is_symlink() or not root.is_dir() or
            root.parent.resolve() != tmp or root.resolve().parent != tmp or
            not root.name.startswith('astra-synth-')):
        raise ValueError('only an existing isolated astra-synth-* folder under system temp')
    for name in ('app', 'data', 'tests'):
        target = root / name
        if target.is_symlink() or not target.is_dir() or target.resolve().parent != root.resolve():
            raise ValueError('unsafe preview subdirectory')
    return root


def _added_files(table: AlternateSyntheticTable, plan: QueryPlan) -> dict[str, str]:
    serialized = table.model_dump_json(indent=2) + '\n'
    digest = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    return {
        'app/extended.py': EXTENDED_SOURCE.replace('__FIXTURE_SHA256__', digest),
        'data/query_physical_fixture.json': serialized,
        'data/query_cases.json': plan.model_dump_json(indent=2) + '\n',
        'tests/test_embedded_query.py': GENERATED_TEST,
        'README_EXTENDED.md': README_EXTENDED,
    }


def _subprocess_acceptance(root: Path) -> None:
    # A separate interpreter prevents `app` module collisions with previous tests.
    run = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                          'tests/test_app.py', 'tests/test_embedded_query.py'],
                         cwd=root, capture_output=True, text=True, timeout=35)
    if run.returncode:
        raise ValueError('generated project self-test failed: ' + run.stdout[-1100:] + run.stderr[-400:])


def embed_in_preview(table: AlternateSyntheticTable, plan: QueryPlan, root: Path) -> EmbeddedQueryReport:
    """Attach a fixed read-only endpoint to an already checked generated preview.

    No overwrite, no edits to app/main.py. Input expectations prechecked before writes.
    """
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    plan = QueryPlan.model_validate(plan.model_dump(mode='json'))
    bound_query = verify_query_plan(table, plan)  # independently specified IDs, strict types
    root = _safe_root(Path(root))
    base = check_generated_preview(root)  # exact original fixed-template and blocked preflight
    files = _added_files(table, plan)
    report_name = 'data/query_embed_report.json'
    if any((root / rel).exists() or (root / rel).is_symlink() for rel in [*files, report_name]):
        raise ValueError('query extension exists; overwrite is forbidden')
    if (root / 'app/main.py').read_text(encoding='utf-8') != APP or (root / 'app/index.html').read_text(encoding='utf-8') != HTML:
        raise ValueError('protected generated templates were altered')
    for rel, content in files.items():
        with (root / rel).open('x', encoding='utf-8') as f:
            f.write(content)
    _subprocess_acceptance(root)
    report = EmbeddedQueryReport(
        physical_table_sha256=fingerprint(table), query_cases_sha256=fingerprint(plan),
        base_preview_sha256=fingerprint(base), accepted_cases=bound_query.pass_count,
    )
    with (root / report_name).open('x', encoding='utf-8') as f:
        f.write(report.model_dump_json(indent=2) + '\n')
    return report


def generate_integrated_preview(bundle: ObservationBundle, evidence_root: Path,
                                canonical_schema: OwnedSchemaDeclaration,
                                request: GenerationRequest, table: AlternateSyntheticTable,
                                acceptance: SchemaAcceptanceCases, plan: QueryPlan,
                                destination: Path) -> EmbeddedQueryReport:
    """One-command fictional bundle→generated app→embedded query→real generated tests."""
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    plan = QueryPlan.model_validate(plan.model_dump(mode='json'))
    verify_query_plan(table, plan)  # fail before creating anything
    run_schema_reuse(bundle, evidence_root, canonical_schema, request,
                     table, acceptance, destination)
    return embed_in_preview(table, plan, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Generated synthetic app with embedded read-only typed query route')
    for name in ('observation', 'evidence_root', 'canonical_schema', 'generation_request',
                 'synthetic_physical_table', 'feature_cases', 'query_cases', 'empty_temp_destination'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.canonical_schema.read_text(encoding='utf-8'))
        request = GenerationRequest.model_validate_json(args.generation_request.read_text(encoding='utf-8'))
        table = AlternateSyntheticTable.model_validate_json(args.synthetic_physical_table.read_text(encoding='utf-8'))
        feature_cases = SchemaAcceptanceCases.model_validate_json(args.feature_cases.read_text(encoding='utf-8'))
        query_cases = QueryPlan.model_validate_json(args.query_cases.read_text(encoding='utf-8'))
        result = generate_integrated_preview(bundle, args.evidence_root, schema, request,
                                             table, feature_cases, query_cases, args.empty_temp_destination)
    except (OSError, UnicodeError, ValueError, ValidationError, RuntimeError, TypeError,
            subprocess.SubprocessError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
