"""One-command *fictional-only* manual action -> draft -> isolated smoke app.

This deliberately does not replay or verify the source website. It checks that
one operator-supplied JSON trace and one ObservationBundle agree on their
claimed action/state transition, then tests an unrelated fixed synthetic app.
Any apparent 'observed' certainty remains an unverified operator claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.data_mapping import OwnedSchemaDeclaration, compare_mappings
from astra_contracts.evidence_integrity import _read_capture
from astra_contracts.functional_spec import derive_spec
from astra_contracts.generation_contract import GenerationRequest, fingerprint, preflight_contract
from astra_contracts.observation import Certainty, EvidenceKind, ObservationBundle
from astra_contracts.synthetic_acceptance import check_generated_preview
from astra_contracts.synthetic_bridge import generate_bridge_preview
from astra_contracts.synthetic_generator import SyntheticDemo


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ManualTrace(ClosedModel):
    version: Literal['0.1'] = '0.1'
    provenance: Literal['unverified_operator_supplied_manual_test']
    observation_id: str = Field(min_length=2, max_length=64)
    evidence_id: str = Field(min_length=2, max_length=64)
    action: str = Field(min_length=1, max_length=250)
    before: dict[str, str | int | float | bool | None]
    after: dict[str, str | int | float | bool | None]
    original_site_behavior_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    approval_granted: Literal[False] = False

    @model_validator(mode='after')
    def must_record_a_change(self):
        common = set(self.before) & set(self.after)
        if not common or not any(self.before[k] != self.after[k] for k in common):
            raise ValueError('manual trace must contain a changed shared state field')
        return self


class ManualPipelineReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['fictional_end_to_end_smoke_passed'] = 'fictional_end_to_end_smoke_passed'
    source_kind: Literal['unverified_operator_supplied_manual_test'] = 'unverified_operator_supplied_manual_test'
    observation_sha256: str
    action_trace_sha256: str
    functional_spec_sha256: str
    mapping_report_sha256: str
    blocked_contract_sha256: str
    synthetic_fixture_sha256: str
    original_observation_id: str
    synthetically_illustrated_feature: str
    synthetic_checks_passed: int = Field(ge=1)
    synthetic_generated_file_count: int = Field(ge=8)
    mapping_discrepancy_count: int = Field(ge=0)
    original_site_behavior_verified: Literal[False] = False
    reviewer_identity_verified: Literal[False] = False
    original_calculation_verified: Literal[False] = False
    customer_database_accessed: Literal[False] = False
    customer_schema_approved: Literal[False] = False
    actual_code_generation_authorized: Literal[False] = False
    production_ready: Literal[False] = False
    deployment_authorized: Literal[False] = False


def verify_manual_trace(bundle: ObservationBundle, evidence_root: Path) -> tuple[ManualTrace, str]:
    """Check exact *reported* trace-vs-observation agreement, NOT source truth."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    if len(bundle.observations) != 1 or len(bundle.evidence) != 1:
        raise ValueError('v0.1 one-unit pipeline accepts exactly one observation and one trace')
    observed = bundle.observations[0]
    evidence = bundle.evidence[0]
    if (observed.certainty is not Certainty.OBSERVED or
            evidence.kind is not EvidenceKind.MANUAL_TEST or
            evidence.id not in observed.evidence_ids or len(observed.evidence_ids) != 1):
        raise ValueError('one explicitly claimed observed action with linked manual-test JSON is required')
    if not evidence.source_ref.endswith('.json'):
        raise ValueError('manual-test trace must be sanitized JSON')
    if not observed.action:
        raise ValueError('observation does not declare an action')
    raw = _read_capture(Path(evidence_root), evidence)
    trace = ManualTrace.model_validate_json(raw)
    canonical = lambda state: json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if (trace.observation_id != observed.id or trace.evidence_id != evidence.id or
            trace.action != observed.action or canonical(trace.before) != canonical(observed.before) or
            canonical(trace.after) != canonical(observed.after)):
        raise ValueError('manual trace and observation disagree on ID/action/before/after')
    # The trace must represent a visible state transition in the narrative, not
    # just the existence of a file or a one-sided state assignment.
    return trace, hashlib.sha256(raw).hexdigest()


def run_pipeline(bundle: ObservationBundle, evidence_root: Path,
                 synthetic_schema: OwnedSchemaDeclaration, request: GenerationRequest,
                 demo: SyntheticDemo, empty_destination: Path) -> ManualPipelineReport:
    """End-to-end only for a separately fictional fixed-code FastAPI/SQLite app."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    synthetic_schema = OwnedSchemaDeclaration.model_validate(synthetic_schema.model_dump(mode='json'))
    request = GenerationRequest.model_validate(request.model_dump(mode='json'))
    demo = SyntheticDemo.model_validate(demo.model_dump(mode='json'))
    trace, trace_digest = verify_manual_trace(bundle, evidence_root)
    if synthetic_schema.source_kind != 'synthetic_fixture':
        raise ValueError('real/owner-provided schema is not permitted for this fictional pipeline')
    if request.mode != 'contract_only' or request.stack != 'fastapi_sqlite':
        raise ValueError('only isolated fixed FastAPI/SQLite synthetic smoke is supported')
    draft = derive_spec(bundle)
    if len(draft.candidate_features) != 1 or draft.candidate_features[0].observation_id != trace.observation_id:
        raise ValueError('source trace did not become exactly one unapproved draft feature')
    report = compare_mappings(draft, synthetic_schema)
    blocked = preflight_contract(draft, synthetic_schema, report, request)
    if blocked.status != 'blocked_pending_review' or 'independent_generation_not_authorized' not in blocked.block_reasons:
        raise ValueError('fail-closed production authorization was lost')

    # Existing generator is restricted to an *empty*, guarded astra-synth-* temp folder.
    paths = generate_bridge_preview(draft, synthetic_schema, report, request,
                                    blocked, demo, Path(empty_destination))
    acceptance = check_generated_preview(Path(empty_destination))
    if (acceptance.synthetic_fixture_sha256 != fingerprint(demo) or
            len(acceptance.checks) < 10 or
            not any(s.startswith('trace_route_') for s in acceptance.checks)):
        raise ValueError('generated synthetic acceptance was incomplete')
    summary = ManualPipelineReport(
        observation_sha256=fingerprint(bundle), action_trace_sha256=trace_digest,
        functional_spec_sha256=fingerprint(draft), mapping_report_sha256=fingerprint(report),
        blocked_contract_sha256=fingerprint(blocked), synthetic_fixture_sha256=fingerprint(demo),
        original_observation_id=trace.observation_id,
        synthetically_illustrated_feature=draft.candidate_features[0].feature.value,
        synthetic_checks_passed=len(acceptance.checks),
        synthetic_generated_file_count=len(paths),
        mapping_discrepancy_count=sum(f.status != 'structurally_compatible_unapproved' for f in report.findings),
    )
    path = Path(empty_destination) / 'data' / 'manual_pipeline_report.json'
    with path.open('x', encoding='utf-8') as f:
        f.write(summary.model_dump_json(indent=2) + '\n')
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Fictional/manual-trace-to-smoke E2E only; never source-site validation')
    parser.add_argument('observation', type=Path)
    parser.add_argument('evidence_root', type=Path)
    parser.add_argument('synthetic_schema', type=Path)
    parser.add_argument('generation_request', type=Path)
    parser.add_argument('synthetic_demo', type=Path)
    parser.add_argument('empty_temp_destination', type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        schema = OwnedSchemaDeclaration.model_validate_json(args.synthetic_schema.read_text(encoding='utf-8'))
        request = GenerationRequest.model_validate_json(args.generation_request.read_text(encoding='utf-8'))
        demo = SyntheticDemo.model_validate_json(args.synthetic_demo.read_text(encoding='utf-8'))
        result = run_pipeline(bundle, args.evidence_root, schema, request, demo, args.empty_temp_destination)
    except (OSError, UnicodeError, ValueError, ValidationError, ImportError, RuntimeError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
