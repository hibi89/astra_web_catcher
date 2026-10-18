"""Step 4-B: offline diagnostic comparison of a draft UI spec and *declared* owned schema.

No database or API connection; no field-name inference, migration, writes, or approval.
Run: python -m astra_contracts.data_mapping <functional_spec.json> <declared_schema.json>
The output is JSON printed to stdout only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.functional_spec import FunctionalSpecDraft


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class DataType(str, Enum):
    STRING = 'string'
    INTEGER = 'integer'
    NUMBER = 'number'
    BOOLEAN = 'boolean'
    UNKNOWN = 'unknown'


class SchemaField(StrictModel):
    name: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    data_type: DataType
    nullable: bool = False


class Resource(StrictModel):
    id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    kind: Literal['db_table', 'api_response']
    fields: list[SchemaField] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique_fields(self):
        names = [x.name for x in self.fields]
        if len(names) != len(set(names)):
            raise ValueError('duplicate field names')
        return self


class ExplicitBinding(StrictModel):
    observation_id: str
    ui_field: str
    resource_id: str
    resource_field: str


class OwnedSchemaDeclaration(StrictModel):
    schema_version: Literal['0.1']
    source_kind: Literal['synthetic_fixture', 'owner_supplied_document']
    source_label: str = Field(min_length=1, max_length=200)
    resources: list[Resource] = Field(min_length=1, max_length=200)
    bindings: list[ExplicitBinding] = Field(default_factory=list, max_length=5000)

    @model_validator(mode='after')
    def uniqueness(self):
        ids = [x.id for x in self.resources]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate resource IDs')
        keys = [(x.observation_id, x.ui_field) for x in self.bindings]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate explicit mappings for a UI field')
        return self


class MappingFinding(StrictModel):
    observation_id: str
    ui_field: str
    ui_type: DataType
    resource_id: str | None = None
    resource_field: str | None = None
    declared_type: DataType | None = None
    status: Literal['structurally_compatible_unapproved', 'unmapped', 'missing_resource',
                    'missing_resource_field', 'type_conflict', 'unknown_ui_type',
                    'nullable_conflict']
    detail: str


class MappingReport(StrictModel):
    version: Literal['0.1'] = '0.1'
    spec_source_sha256: str
    declaration_sha256: str
    declaration_source_kind: Literal['synthetic_fixture', 'owner_supplied_document']
    declaration_source_label: str
    status: Literal['review_only'] = 'review_only'
    schema_verified_against_live_system: Literal[False] = False
    mapping_approved: Literal[False] = False
    implementation_ready: Literal[False] = False
    approval_gates: list[str]
    unresolved_observation_ids: list[str]
    findings: list[MappingFinding]
    counts: dict[str, int]


def _kind(value: object) -> DataType:
    # Explicit bool check is essential: in Python bool subclasses int.
    if value is None:
        return DataType.UNKNOWN
    if type(value) is bool:
        return DataType.BOOLEAN
    if type(value) is int:
        return DataType.INTEGER
    if type(value) is float:
        return DataType.NUMBER
    if type(value) is str:
        return DataType.STRING
    return DataType.UNKNOWN


def _ui_type(before: object, after: object) -> DataType:
    candidates = {_kind(v) for v in (before, after)} - {DataType.UNKNOWN}
    if len(candidates) == 1:
        return next(iter(candidates))
    if candidates == {DataType.INTEGER, DataType.NUMBER}:
        return DataType.NUMBER
    return DataType.UNKNOWN


def _fingerprint(model: BaseModel) -> str:
    serial = json.dumps(model.model_dump(mode='json'), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(serial.encode('utf-8')).hexdigest()


def compare_mappings(spec: FunctionalSpecDraft, declaration: OwnedSchemaDeclaration) -> MappingReport:
    """Pure deterministic diagnostic. Even compatible entries are unapproved and unverified."""
    spec = FunctionalSpecDraft.model_validate(spec.model_dump(mode='json'))
    declaration = OwnedSchemaDeclaration.model_validate(declaration.model_dump(mode='json'))
    candidates = {(c.observation_id, f.field): f for c in spec.candidate_features for f in c.changed_fields}
    bindings = {(b.observation_id, b.ui_field): b for b in declaration.bindings}
    unknown_bindings = sorted(set(bindings) - set(candidates))
    if unknown_bindings:
        raise ValueError(f'bindings reference nonexistent candidate fields: {unknown_bindings}')

    resources = {r.id: r for r in declaration.resources}
    findings: list[MappingFinding] = []
    for (observation_id, ui_field), changed in sorted(candidates.items()):
        actual_type = _ui_type(changed.before, changed.after)
        binding = bindings.get((observation_id, ui_field))
        resource = resources.get(binding.resource_id) if binding else None
        field = next((f for f in resource.fields if f.name == binding.resource_field), None) if resource and binding else None
        detail = ''
        if not binding:
            status, detail = 'unmapped', 'No explicit binding was supplied; ASTRA must not guess column names.'
        elif resource is None:
            status, detail = 'missing_resource', 'Explicit resource identifier was not declared.'
        elif field is None:
            status, detail = 'missing_resource_field', 'Explicit field does not exist in the declared resource.'
        elif actual_type is DataType.UNKNOWN:
            status, detail = 'unknown_ui_type', 'UI value type is absent, mixed or not safely comparable.'
        elif (changed.before is None or changed.after is None) and not field.nullable:
            status, detail = 'nullable_conflict', 'UI contains null while declared source field is non-nullable.'
        elif not (actual_type == field.data_type or actual_type is DataType.INTEGER and field.data_type is DataType.NUMBER):
            status, detail = 'type_conflict', 'Observed UI scalar type disagrees with declared field type; no conversion assumed.'
        else:
            status, detail = 'structurally_compatible_unapproved', 'Structural match only; no semantic or live-data verification or authorization.'
        findings.append(MappingFinding(observation_id=observation_id, ui_field=ui_field,
            ui_type=actual_type, resource_id=binding.resource_id if binding else None,
            resource_field=binding.resource_field if binding else None,
            declared_type=field.data_type if field else None, status=status, detail=detail))

    counts = {status: sum(f.status == status for f in findings) for status in
              ('structurally_compatible_unapproved', 'unmapped', 'missing_resource',
               'missing_resource_field', 'type_conflict', 'unknown_ui_type', 'nullable_conflict')}
    return MappingReport(spec_source_sha256=_fingerprint(spec), declaration_sha256=_fingerprint(declaration),
        declaration_source_kind=declaration.source_kind, declaration_source_label=declaration.source_label,
        approval_gates=sorted(set([g.key for g in spec.approval_gates] + [
            'verify_declared_schema_against_owned_system', 'confirm_mapping_semantics', 'approve_any_source_changes'])),
        unresolved_observation_ids=sorted({u.observation_id for u in spec.unresolved}),
        findings=findings, counts=counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Compare a draft UI spec to a supplied, offline DB/API schema declaration')
    parser.add_argument('spec', type=Path)
    parser.add_argument('schema', type=Path)
    args = parser.parse_args(argv)
    try:
        spec = FunctionalSpecDraft.model_validate_json(args.spec.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.schema.read_text(encoding='utf-8'))
        report = compare_mappings(spec, schema)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
