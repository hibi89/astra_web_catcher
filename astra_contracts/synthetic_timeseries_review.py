"""Review only explicit synthetic time-series bindings for chart/table mode switching."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROLES = ('entity_identifier', 'time_period', 'numeric_measure', 'aggregation_semantics')
EXPECTED = {'entity_identifier': {'string'}, 'time_period': {'string'},
            'numeric_measure': {'number', 'integer'}, 'aggregation_semantics': {'string'}}
TYPES = {'string', 'number', 'integer', 'boolean'}
IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


def review(data: dict) -> dict:
    """Fail closed for malformed fixtures; never infer mappings or grant approval."""
    if not isinstance(data, dict) or set(data) != {'source_kind', 'dataset_id', 'columns', 'proposed_bindings'}:
        raise ValueError('invalid fixture fields')
    if data['source_kind'] != 'synthetic_fixture':
        raise ValueError('only synthetic fixtures allowed')
    if not isinstance(data['dataset_id'], str) or not IDENTIFIER.fullmatch(data['dataset_id']):
        raise ValueError('invalid dataset identifier')
    cols = data['columns']
    if not isinstance(cols, list) or len(cols) > 100:
        raise ValueError('invalid columns')
    names = {}
    for col in cols:
        if not isinstance(col, dict) or set(col) != {'name', 'kind'}:
            raise ValueError('invalid column declaration')
        name, kind = col['name'], col['kind']
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or kind not in TYPES or name in names:
            raise ValueError('invalid or duplicate column')
        names[name] = kind
    bindings = data['proposed_bindings']
    if not isinstance(bindings, dict) or set(bindings) - set(ROLES):
        raise ValueError('unknown semantic roles')
    findings = {}
    for role in ROLES:
        target = bindings.get(role)
        if target is None:
            status = 'missing_explicit_binding'
        elif not isinstance(target, str) or not IDENTIFIER.fullmatch(target):
            raise ValueError('invalid binding identifier')
        elif target not in names:
            status = 'missing_column'
        elif names[target] not in EXPECTED[role]:
            status = 'type_mismatch'
        else:
            status = 'structurally_compatible_unapproved'
        findings[role] = {'column': target, 'status': status}
    return {'skill_id': 'chart_table_mode_switch', 'source_kind': 'synthetic_fixture',
            'dataset_id': data['dataset_id'], 'findings': findings,
            'missing_or_incompatible': [k for k, v in findings.items() if v['status'] != 'structurally_compatible_unapproved'],
            'semantic_approval_verified': False, 'reference_formula_verified': False,
            'owner_database_access_authorized': False, 'code_generation_authorized': False,
            'deployment_authorized': False, 'generation_contract': 'blocked_pending_review'}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args(argv)
    try:
        result = review(json.loads(args.fixture.read_text(encoding='utf-8')))
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
