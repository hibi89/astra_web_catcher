"""Reuse one *fictional-only* FastAPI acceptance adapter across physical field names.

Explicitly declared source field bindings normalize distinct made-up table shapes
into the SAME fixed SyntheticDemo contract. No schema inference, external source,
customer DB, approval, formula verification, or production code generation.

CLI: python -m astra_contracts.schema_reuse_adapter OBSERVATION EVIDENCE_ROOT \
     CANONICAL_SCHEMA GENERATION_REQUEST SOURCE_FIXTURE ACCEPTANCE_CASES EMPTY_TEMP_DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError, model_validator

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.feature_acceptance_adapter import (
    FeatureCase, FeatureAcceptancePlan, _expected_from_fixture, run_feature_acceptance,
)
from astra_contracts.generation_contract import GenerationRequest, fingerprint
from astra_contracts.manual_trace_pipeline import run_pipeline
from astra_contracts.observation import Feature, ObservationBundle
from astra_contracts.synthetic_generator import SyntheticDemo, SyntheticRow

LOGICAL_FIELDS = ('id', 'title', 'category', 'score')
FIELD_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SyntheticFieldBinding(ClosedModel):
    logical_field: Literal['id', 'title', 'category', 'score']
    source_field: str = Field(min_length=1, max_length=64)

    @model_validator(mode='after')
    def valid_source_field(self):
        if not FIELD_RE.fullmatch(self.source_field):
            raise ValueError('source field must be a simple, non-executable identifier')
        return self


class AlternateSyntheticTable(ClosedModel):
    version: Literal['0.1'] = '0.1'
    source_kind: Literal['synthetic_fixture']
    run_mode: Literal['temporary_demo_only']
    table_name: str = Field(min_length=2, max_length=64)
    preview_title: str = Field(min_length=1, max_length=100)
    bindings: list[SyntheticFieldBinding] = Field(min_length=4, max_length=4)
    rows: list[dict[str, StrictStr | StrictInt]] = Field(min_length=1, max_length=100)
    original_site_behavior_verified: Literal[False] = False
    customer_database_connected: Literal[False] = False
    schema_mapping_approved: Literal[False] = False

    @model_validator(mode='after')
    def exact_columns(self):
        if not FIELD_RE.fullmatch(self.table_name):
            raise ValueError('table name must be a simple identifier')
        logical = [b.logical_field for b in self.bindings]
        physical = [b.source_field for b in self.bindings]
        if set(logical) != set(LOGICAL_FIELDS) or len(set(physical)) != 4:
            raise ValueError('exactly four distinct logical and physical bindings are required')
        allowed = set(physical)
        for row in self.rows:
            if set(row) != allowed:
                raise ValueError('row columns differ from explicitly bound synthetic columns')
            if any(not FIELD_RE.fullmatch(key) for key in row):
                raise ValueError('invalid row field name')
            if any(isinstance(value, str) and len(value) > 256 for value in row.values()):
                raise ValueError('source row string exceeds bound')
        return self


class SchemaAcceptanceCases(ClosedModel):
    version: Literal['0.1'] = '0.1'
    scope: Literal['synthetic_fixture_only']
    table_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    cases: list[FeatureCase] = Field(min_length=1, max_length=30)
    original_site_verified: Literal[False] = False
    production_authorized: Literal[False] = False

    @model_validator(mode='after')
    def unique(self):
        ids = [case.id for case in self.cases]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate acceptance IDs')
        if not any(c.relationship == 'source_feature_illustration' for c in self.cases):
            raise ValueError('source feature illustration is required')
        return self


class SchemaReuseResult(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['multi_schema_synthetic_only_passed'] = 'multi_schema_synthetic_only_passed'
    physical_table_name: str
    physical_fields: list[str]
    source_fixture_sha256: str
    normalized_fixture_sha256: str
    acceptance_cases_sha256: str
    acceptance_result_sha256: str
    pipeline_report_sha256: str
    normalized_row_count: int = Field(ge=1)
    acceptance_cases_passed: int = Field(ge=1)
    source_illustrations_passed: int = Field(ge=1)
    original_site_behavior_verified: Literal[False] = False
    customer_database_accessed: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def normalize_table(table: AlternateSyntheticTable) -> SyntheticDemo:
    """Translate ONLY four explicit fictional columns. Never use guessed mappings."""
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    binding = {b.logical_field: b.source_field for b in table.bindings}
    items = []
    for row in table.rows:
        result = {logical: row[binding[logical]] for logical in LOGICAL_FIELDS}
        # Strict string/int separation: bool must never become an integer score.
        if any(type(result[key]) is not str for key in ('id', 'title', 'category')):
            raise ValueError('synthetic id/title/category must be strings')
        if type(result['score']) is not int:
            raise ValueError('synthetic score must be a strict integer')
        items.append(SyntheticRow.model_validate(result))
    return SyntheticDemo(schema_version='0.1', source_kind='synthetic_fixture',
                         run_mode='temporary_demo_only', title=table.preview_title, items=items)


def run_schema_reuse(bundle: ObservationBundle, evidence_root: Path,
                     canonical_schema: OwnedSchemaDeclaration, request: GenerationRequest,
                     table: AlternateSyntheticTable, acceptance: SchemaAcceptanceCases,
                     empty_destination: Path) -> SchemaReuseResult:
    """Exact expectations -> existing real API tests for a schema-normalized demo.

    The source's function is *illustrated*, never verified. Source and physical
    fixture metadata are immutable; only guarded temporary synthetic output.
    """
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    canonical_schema = OwnedSchemaDeclaration.model_validate(canonical_schema.model_dump(mode='json'))
    request = GenerationRequest.model_validate(request.model_dump(mode='json'))
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    acceptance = SchemaAcceptanceCases.model_validate(acceptance.model_dump(mode='json'))
    if acceptance.table_sha256 != fingerprint(table):
        raise ValueError('acceptance cases refer to a stale or different physical fixture')
    if canonical_schema.source_kind != 'synthetic_fixture' or request.stack != 'fastapi_sqlite':
        raise ValueError('only the isolated synthetic FastAPI contract is supported')
    demo = normalize_table(table)
    if len(bundle.observations) != 1:
        raise ValueError('expected one separately reported source observation')
    trace_observation = bundle.observations[0]
    if not any(c.relationship == 'source_feature_illustration' and
               c.source_observation_id == trace_observation.id and
               c.feature == trace_observation.feature for c in acceptance.cases):
        raise ValueError('source illustration must match exact original observation/feature')
    # Fail before generating ANY output if the declared expectations are wrong.
    for case in acceptance.cases:
        if case.relationship == 'source_feature_illustration' and (
            case.source_observation_id != trace_observation.id or case.feature != trace_observation.feature
        ):
            raise ValueError('illustration case falsely attributes a foreign source feature')
        status, ids = _expected_from_fixture(case, demo)
        if status != case.expected_status or ids != case.expected_ids:
            raise ValueError(f'fictional acceptance mismatch: {case.id}')
    if not any(c.relationship == 'source_feature_illustration' and
               c.feature is Feature.FILTER and c.expected_ids for c in acceptance.cases):
        raise ValueError('synthetic source filter illustration must return sample rows')

    pipeline = run_pipeline(bundle, evidence_root, canonical_schema, request, demo, empty_destination)
    plan = FeatureAcceptancePlan(scope='synthetic_fixture_only',
                                 source_observation_sha256=fingerprint(bundle),
                                 prior_pipeline_report_sha256=fingerprint(pipeline),
                                 synthetic_fixture_sha256=fingerprint(demo),
                                 cases=acceptance.cases)
    accepted = run_feature_acceptance(bundle, evidence_root, empty_destination, plan)
    if accepted.synthetic_cases_passed != len(acceptance.cases):
        raise ValueError('generated API acceptance coverage incomplete')
    report = SchemaReuseResult(
        physical_table_name=table.table_name,
        physical_fields=sorted(b.source_field for b in table.bindings),
        source_fixture_sha256=fingerprint(table),
        normalized_fixture_sha256=fingerprint(demo),
        acceptance_cases_sha256=fingerprint(acceptance),
        acceptance_result_sha256=fingerprint(accepted),
        pipeline_report_sha256=fingerprint(pipeline),
        normalized_row_count=len(demo.items),
        acceptance_cases_passed=accepted.synthetic_cases_passed,
        source_illustrations_passed=accepted.source_illustrations_passed,
    )
    path = Path(empty_destination) / 'data' / 'schema_reuse_report.json'
    with path.open('x', encoding='utf-8') as output:
        output.write(report.model_dump_json(indent=2) + '\n')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Explicit physical fixture→canonical app acceptance; fictional only')
    for name in ('observation', 'evidence_root', 'canonical_schema', 'generation_request',
                 'source_fixture', 'acceptance_cases', 'empty_temp_destination'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.canonical_schema.read_text(encoding='utf-8'))
        request = GenerationRequest.model_validate_json(args.generation_request.read_text(encoding='utf-8'))
        table = AlternateSyntheticTable.model_validate_json(args.source_fixture.read_text(encoding='utf-8'))
        cases = SchemaAcceptanceCases.model_validate_json(args.acceptance_cases.read_text(encoding='utf-8'))
        result = run_schema_reuse(bundle, args.evidence_root, schema, request, table, cases, args.empty_temp_destination)
    except (OSError, UnicodeError, ValueError, ValidationError, TypeError, RuntimeError, ImportError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
