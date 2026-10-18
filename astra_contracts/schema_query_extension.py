"""Explicit-column sort/equality-filter API for *fictional* ASTRA schema fixtures.

Only physical fields declared in an AlternateSyntheticTable are accepted. This
is a separate read-only FastAPI endpoint, not a mutation of the existing fixed
synthetic preview, a database adapter or an original-website behavior claim.

    python -m astra_contracts.schema_query_extension FIXTURE.json QUERY_CASES.json
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.generation_contract import fingerprint
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable, normalize_table

INT_STRING = re.compile(r'^(0|[1-9][0-9]{0,4})$')


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class QueryCase(ClosedModel):
    id: str = Field(min_length=2, max_length=60, pattern=r'^[a-z][a-z0-9_-]+$')
    sort_by: str = Field(min_length=1, max_length=64)
    direction: Literal['asc', 'desc'] = 'asc'
    filter_by: str | None = Field(default=None, max_length=64)
    filter_value: str | None = Field(default=None, max_length=256)
    limit: int = Field(default=100, ge=1, le=100, strict=True)
    expected_ids: list[str] = Field(max_length=100)
    original_site_behavior_verified: Literal[False] = False

    @model_validator(mode='after')
    def filter_pair(self):
        if (self.filter_by is None) != (self.filter_value is None):
            raise ValueError('filter_by and filter_value must be supplied together')
        if len(self.expected_ids) != len(set(self.expected_ids)):
            raise ValueError('duplicate expected synthetic IDs')
        return self


class QueryPlan(ClosedModel):
    version: Literal['0.1'] = '0.1'
    scope: Literal['synthetic_fixture_only']
    source_table_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    cases: list[QueryCase] = Field(min_length=2, max_length=40)
    user_database_access_authorized: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    deployment_authorized: Literal[False] = False

    @model_validator(mode='after')
    def unique_and_covered(self):
        ids = [c.id for c in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate synthetic query case IDs')
        if not any(c.filter_by is not None for c in self.cases):
            raise ValueError('at least one field filter case is required')
        if not any(c.direction == 'desc' for c in self.cases):
            raise ValueError('descending sort case is required')
        return self


class QueryReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['synthetic_query_contract_passed'] = 'synthetic_query_contract_passed'
    table_name: str
    source_table_sha256: str
    query_plan_sha256: str
    physical_sortable_fields: list[str]
    checked_cases: list[str]
    pass_count: int = Field(ge=2)
    original_site_behavior_verified: Literal[False] = False
    customer_database_accessed: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def _bound_columns(table: AlternateSyntheticTable) -> tuple[dict[str, str], dict[str, str]]:
    bindings = {b.source_field: b.logical_field for b in table.bindings}
    by_logical = {b.logical_field: b.source_field for b in table.bindings}
    return bindings, by_logical


def _typed_filter(raw: str, logical_field: str) -> str | int:
    if logical_field == 'score':
        if not INT_STRING.fullmatch(raw) or int(raw) > 10000:
            raise ValueError('numeric filter must be a nonnegative integer <=10000')
        return int(raw)
    return raw


def select_rows(table: AlternateSyntheticTable, *, sort_by: str, direction: str = 'asc',
                filter_by: str | None = None, filter_value: str | None = None,
                limit: int = 100) -> list[dict[str, str | int]]:
    """Pure in-memory selection of EXPLICIT physical fixture fields; never SQL."""
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    normalize_table(table)  # validate canonical values (including unique IDs)
    allowed, logical_to_physical = _bound_columns(table)
    if sort_by not in allowed or direction not in ('asc', 'desc'):
        raise ValueError('sorting requires an explicitly bound field and direction')
    if (filter_by is None) != (filter_value is None):
        raise ValueError('filter field/value must be paired')
    if type(limit) is not int or not (1 <= limit <= 100):
        raise ValueError('invalid synthetic query limit')
    selected = [dict(row) for row in table.rows]
    if filter_by is not None:
        if filter_by not in allowed:
            raise ValueError('filtering requires an explicitly bound field')
        target = _typed_filter(filter_value, allowed[filter_by])
        selected = [r for r in selected if type(r[filter_by]) is type(target) and r[filter_by] == target]
    # Two stable sorting passes guarantee source-ID tie breaks in ascending order
    # even when the selected sort direction is descending.
    key_id = logical_to_physical['id']
    selected.sort(key=lambda r: r[key_id])
    def key(row):
        value = row[sort_by]
        return value.casefold() if isinstance(value, str) else value
    selected.sort(key=key, reverse=direction == 'desc')
    return selected[:limit]


def create_query_app(table: AlternateSyntheticTable) -> FastAPI:
    """Bound, read-only route usable with TestClient or a localhost ASGI server."""
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    normalize_table(table)
    app = FastAPI(title='ASTRA fictional query fixture', docs_url=None,
                  redoc_url=None, openapi_url=None)

    @app.get('/api/rows')
    def query_rows(sort_by: str, direction: Literal['asc', 'desc'] = 'asc',
                   filter_by: str | None = None, filter_value: str | None = None,
                   limit: int = Query(100, ge=1, le=100)):
        try:
            rows = select_rows(table, sort_by=sort_by, direction=direction,
                               filter_by=filter_by, filter_value=filter_value, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {'synthetic': True, 'source_kind': 'synthetic_fixture',
                'table_name': table.table_name, 'items': rows,
                'original_site_behavior_verified': False}

    return app


def verify_query_plan(table: AlternateSyntheticTable, plan: QueryPlan) -> QueryReport:
    """Independently authored expected IDs must match the actual FastAPI output."""
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    plan = QueryPlan.model_validate(plan.model_dump(mode='json'))
    if fingerprint(table) != plan.source_table_sha256:
        raise ValueError('stale synthetic table SHA; do not reuse foreign assertions')
    normalize_table(table)
    logical_to_physical = {b.logical_field: b.source_field for b in table.bindings}
    id_column = logical_to_physical['id']
    schema_columns = set(logical_to_physical.values())
    with TestClient(create_query_app(table)) as client:
        for case in plan.cases:
            params = {'sort_by': case.sort_by, 'direction': case.direction,
                      'limit': case.limit}
            if case.filter_by is not None:
                params['filter_by'] = case.filter_by
                params['filter_value'] = case.filter_value
            response = client.get('/api/rows', params=params)
            if response.status_code != 200:
                raise ValueError(f'query API returned {response.status_code}: {case.id}')
            body = response.json()
            if body.get('synthetic') is not True or body.get('original_site_behavior_verified') is not False:
                raise ValueError('synthetic API missing safety markers')
            actual = body.get('items')
            if not isinstance(actual, list) or any(set(row) != schema_columns for row in actual):
                raise ValueError(f'query API returned wrong physical columns: {case.id}')
            actual_ids = [row[id_column] for row in actual]
            if actual_ids != case.expected_ids:
                raise ValueError(f'query API mismatched authored expected IDs: {case.id}')
            expected = select_rows(table, sort_by=case.sort_by, direction=case.direction,
                                   filter_by=case.filter_by, filter_value=case.filter_value,
                                   limit=case.limit)
            if actual != expected:
                raise ValueError(f'query API mismatched typed fixture rows: {case.id}')
    return QueryReport(table_name=table.table_name,
                       source_table_sha256=fingerprint(table), query_plan_sha256=fingerprint(plan),
                       physical_sortable_fields=sorted(schema_columns),
                       checked_cases=[case.id for case in plan.cases], pass_count=len(plan.cases))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Read-only synthetic sorted/typed-filter query test')
    parser.add_argument('synthetic_table', type=Path)
    parser.add_argument('query_plan', type=Path)
    args = parser.parse_args(argv)
    try:
        table = AlternateSyntheticTable.model_validate_json(args.synthetic_table.read_text(encoding='utf-8'))
        plan = QueryPlan.model_validate_json(args.query_plan.read_text(encoding='utf-8'))
        report = verify_query_plan(table, plan)
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
