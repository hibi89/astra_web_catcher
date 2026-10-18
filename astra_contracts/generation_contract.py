"""ASTRA Step 4-C: offline, fail-closed *planning contract* for isolated app generation.

This does not generate executable code, write files, connect to a user service,
validate user approval, or deploy anything. All output goes to stdout.

CLI: python -m astra_contracts.generation_contract SPEC SCHEMA REPORT REQUEST
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


# This enum is intentionally small; expanding it requires a separate reviewed change.
STACK_FILES = {
    'fastapi_sqlite': ('app/main.py', 'app/db.py', 'tests/test_app.py', 'README.md'),
    'nextjs_prisma': ('app/page.tsx', 'lib/data.ts', 'tests/app.spec.ts', 'README.md'),
}
RESTRICTED_PATH_COMPONENTS = {
    'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)),
    *(f'lpt{i}' for i in range(1, 10)),
}


class GenerationRequest(ClosedModel):
    version: Literal['0.1']
    mode: Literal['contract_only']
    scope: Literal['new_isolated_project']
    stack: Literal['fastapi_sqlite', 'nextjs_prisma']
    destination: str = Field(min_length=1, max_length=150)

    @field_validator('destination')
    @classmethod
    def safe_destination(cls, text: str) -> str:
        # POSIX-looking paths only. No OS-dependent normalization, glob or symlink access.
        if (text.startswith('/') or '\\' in text or ':' in text or '//' in text
                or text.startswith('~') or '\x00' in text or not re.fullmatch(r'[A-Za-z0-9_./-]+', text)):
            raise ValueError('destination must be a plain relative portable path')
        parts = PurePosixPath(text).parts
        if not parts or any(p in ('', '.', '..') or p.startswith('.') or p.split('.', 1)[0].lower() in RESTRICTED_PATH_COMPONENTS or p.endswith('.') for p in parts):
            raise ValueError('destination must not traverse, hide, or use reserved names')
        if str(PurePosixPath(text)) != text:
            raise ValueError('destination must be canonical')
        return text


class GenerationContract(ClosedModel):
    version: Literal['0.1'] = '0.1'
    mode: Literal['contract_only'] = 'contract_only'
    status: Literal['blocked_pending_review'] = 'blocked_pending_review'
    code_generated: Literal[False] = False
    files_written: Literal[False] = False
    deployment_permitted: Literal[False] = False
    data_mutation_permitted: Literal[False] = False
    approval_verified: Literal[False] = False
    request_sha256: str
    spec_sha256: str
    schema_sha256: str
    report_sha256: str
    observed_candidate_ids: list[str]
    planned_file_paths: list[str]
    block_reasons: list[str]
    existing_approval_gates: list[str]
    required_future_reviews: list[str]


def fingerprint(model: BaseModel) -> str:
    payload = json.dumps(model.model_dump(mode='json'), sort_keys=True,
                         separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def preflight_contract(
    spec: FunctionalSpecDraft,
    schema: OwnedSchemaDeclaration,
    supplied_report: MappingReport,
    request: GenerationRequest,
) -> GenerationContract:
    """Cross-verify every input; return a *blocked*, non-executable manifest.

    A compatible field is NOT an approval. The report must equal a fresh pure
    recomputation so that deleting mismatches cannot bypass the preflight.
    """
    spec = FunctionalSpecDraft.model_validate(spec.model_dump(mode='json'))
    schema = OwnedSchemaDeclaration.model_validate(schema.model_dump(mode='json'))
    supplied_report = MappingReport.model_validate(supplied_report.model_dump(mode='json'))
    request = GenerationRequest.model_validate(request.model_dump(mode='json'))

    recomputed = compare_mappings(spec, schema)
    if supplied_report.model_dump(mode='json') != recomputed.model_dump(mode='json'):
        raise ValueError('mapping report does not match the declared spec and owned-schema manifest')
    if not request.destination:
        raise ValueError('empty destination')

    reasons = {'functional_spec_unapproved', 'mapping_unapproved',
               'schema_not_verified_live', 'independent_generation_not_authorized'}
    if schema.source_kind == 'synthetic_fixture':
        reasons.add('schema_is_synthetic')
    if spec.unresolved:
        reasons.add('unresolved_observations')
    if not spec.candidate_features:
        reasons.add('no_observed_feature_candidates')
    if any(x.status != 'structurally_compatible_unapproved' for x in recomputed.findings):
        reasons.add('mapping_discrepancies')
    if any(c.evidence_quality.value == 'archived_secondary' for c in spec.candidate_features):
        reasons.add('archived_evidence_requires_reverification')

    return GenerationContract(
        request_sha256=fingerprint(request), spec_sha256=fingerprint(spec),
        schema_sha256=fingerprint(schema), report_sha256=fingerprint(supplied_report),
        observed_candidate_ids=sorted(c.observation_id for c in spec.candidate_features),
        planned_file_paths=[f'{request.destination}/{x}' for x in STACK_FILES[request.stack]],
        block_reasons=sorted(reasons),
        existing_approval_gates=sorted(set(recomputed.approval_gates)),
        required_future_reviews=[
            'verify_reference_behaviors_and_formulas',
            'verify_owned_schema_and_semantic_field_bindings',
            'approve_independent_code_generation_and_isolated_workspace',
            'authorize_any_external_access_write_or_deployment_separately',
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline, fail-closed independent-app generation contract')
    parser.add_argument('functional_spec', type=Path)
    parser.add_argument('owned_schema', type=Path)
    parser.add_argument('mapping_report', type=Path)
    parser.add_argument('request', type=Path)
    args = parser.parse_args(argv)
    try:
        spec = FunctionalSpecDraft.model_validate_json(args.functional_spec.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.owned_schema.read_text(encoding='utf-8'))
        report = MappingReport.model_validate_json(args.mapping_report.read_text(encoding='utf-8'))
        request = GenerationRequest.model_validate_json(args.request.read_text(encoding='utf-8'))
        result = preflight_contract(spec, schema, report, request)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
