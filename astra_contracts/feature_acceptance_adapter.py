"""Evidence-labelled, fixture-only feature acceptance adapter for an ASTRA demo.

This verifies *operator-declared synthetic expectations* against a fixed generated
FastAPI/SQLite sample, not original-site functionality. It never grants consent,
changes source observations, connects to customer systems, or deploys.

CLI: python -m astra_contracts.feature_acceptance_adapter OBSERVATION EVIDENCE_ROOT GENERATED_TEMP_DIR PLAN
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Literal

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.generation_contract import fingerprint
from astra_contracts.manual_trace_pipeline import ManualPipelineReport, verify_manual_trace
from astra_contracts.observation import Feature, ObservationBundle
from astra_contracts.synthetic_acceptance import _safe_file, check_generated_preview
from astra_contracts.synthetic_bridge import SyntheticBridgeTrace
from astra_contracts.synthetic_generator import APP, SyntheticDemo


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class FeatureCase(ClosedModel):
    id: str = Field(min_length=2, max_length=64, pattern=r'^[a-z][a-z0-9_-]+$')
    feature: Literal[Feature.LIST, Feature.SEARCH, Feature.FILTER, Feature.DETAIL]
    relationship: Literal['source_feature_illustration', 'independent_synthetic_fixture']
    source_observation_id: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    q: str | None = Field(default=None, min_length=1, max_length=100)
    item_id: str | None = Field(default=None, max_length=40, pattern=r'^[a-z][a-z0-9_-]*$')
    limit: int | None = Field(default=None, ge=1, le=100, strict=True)
    expected_status: Literal[200, 404] = 200
    expected_ids: list[str] = Field(max_length=100)

    @model_validator(mode='after')
    def shape_and_scope(self):
        if self.relationship == 'source_feature_illustration' and not self.source_observation_id:
            raise ValueError('source illustration requires an observation ID')
        if self.relationship == 'independent_synthetic_fixture' and self.source_observation_id is not None:
            raise ValueError('independent fixture test cannot impersonate a source observation')
        if self.feature is Feature.LIST:
            if self.category is not None or self.q is not None or self.item_id is not None:
                raise ValueError('list accepts only optional limit')
        elif self.feature is Feature.FILTER:
            if self.category is None or self.q is not None or self.item_id is not None or self.limit is not None:
                raise ValueError('filter accepts only category')
        elif self.feature is Feature.SEARCH:
            if self.q is None or self.category is not None or self.item_id is not None or self.limit is not None:
                raise ValueError('search accepts only q')
        else:
            if self.item_id is None or self.category is not None or self.q is not None or self.limit is not None:
                raise ValueError('detail accepts only item_id')
        if self.expected_status == 404 and (self.feature is not Feature.DETAIL or self.expected_ids):
            raise ValueError('404 only supported for nonexistent detail with zero expected IDs')
        if self.feature is Feature.DETAIL and self.expected_status == 200 and len(self.expected_ids) != 1:
            raise ValueError('successful detail must expect exactly one item ID')
        if len(set(self.expected_ids)) != len(self.expected_ids):
            raise ValueError('duplicate expected IDs')
        return self


class FeatureAcceptancePlan(ClosedModel):
    version: Literal['0.1'] = '0.1'
    scope: Literal['synthetic_fixture_only']
    source_observation_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    prior_pipeline_report_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    synthetic_fixture_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    original_site_verified: Literal[False] = False
    customer_database_permitted: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    cases: list[FeatureCase] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def unique_cases(self):
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate acceptance case ID')
        if not any(c.relationship == 'source_feature_illustration' for c in self.cases):
            raise ValueError('at least one source-feature illustration is required')
        return self


class FeatureAcceptanceResult(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['synthetic_feature_contract_passed'] = 'synthetic_feature_contract_passed'
    plan_sha256: str
    source_observation_id: str
    pipeline_report_sha256: str
    synthetic_cases_passed: int = Field(ge=1)
    source_illustrations_passed: int = Field(ge=1)
    fixture_only_cases_passed: int = Field(ge=0)
    cases: list[str]
    original_site_behavior_verified: Literal[False] = False
    human_review_authenticated: Literal[False] = False
    customer_database_accessed: Literal[False] = False
    code_generation_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False


def _expected_from_fixture(case: FeatureCase, demo: SyntheticDemo) -> tuple[int, list[str]]:
    """Independent, explicit fixture oracle; never interpret original site prose."""
    rows = sorted(demo.items, key=lambda row: (-row.score, row.id))
    if case.feature is Feature.LIST:
        selected = rows[:case.limit or 50]
    elif case.feature is Feature.FILTER:
        selected = [row for row in rows if row.category == case.category]
    elif case.feature is Feature.SEARCH:
        selected = [row for row in rows if (case.q or '').lower() in row.title.lower()]
    else:
        selected = [row for row in rows if row.id == case.item_id]
        if not selected:
            return 404, []
    return 200, [row.id for row in selected]


def _endpoint(case: FeatureCase) -> tuple[str, dict[str, str | int]]:
    if case.feature is Feature.DETAIL:
        return '/api/items/' + (case.item_id or ''), {}
    if case.feature is Feature.LIST:
        return '/api/items', {'limit': case.limit or 50}
    if case.feature is Feature.FILTER:
        return '/api/items', {'category': case.category or ''}
    return '/api/items', {'q': case.q or ''}


def run_feature_acceptance(bundle: ObservationBundle, evidence_root: Path,
                           preview_root: Path, plan: FeatureAcceptancePlan) -> FeatureAcceptanceResult:
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    plan = FeatureAcceptancePlan.model_validate(plan.model_dump(mode='json'))
    if plan.source_observation_sha256 != fingerprint(bundle):
        raise ValueError('plan refers to a different source observation bundle')

    trace, raw_digest = verify_manual_trace(bundle, Path(evidence_root))
    # Also verifies guarded temp root, byte-exact app/HTML templates, blocked
    # contract, synthetic seed and real independent API/SQLite smoke behavior.
    check_generated_preview(Path(preview_root))
    report_path = _safe_file(Path(preview_root), 'data/manual_pipeline_report.json')
    report = ManualPipelineReport.model_validate_json(report_path.read_text(encoding='utf-8'))
    generated_trace = SyntheticBridgeTrace.model_validate_json(
        _safe_file(Path(preview_root), 'data/astra_preview_trace.json').read_text(encoding='utf-8'))
    demo = SyntheticDemo.model_validate_json(
        _safe_file(Path(preview_root), 'data/seed.json').read_text(encoding='utf-8'))
    if (plan.prior_pipeline_report_sha256 != fingerprint(report) or
        report.observation_sha256 != fingerprint(bundle) or
        report.action_trace_sha256 != raw_digest or
        report.original_observation_id != trace.observation_id or
        report.synthetically_illustrated_feature != bundle.observations[0].feature.value or
        report.synthetic_fixture_sha256 != fingerprint(demo) or
        plan.synthetic_fixture_sha256 != fingerprint(demo) or
        report.functional_spec_sha256 != generated_trace.functional_spec_sha256):
        raise ValueError('source action, generated trace, fixture or prior report mismatch')

    if not any(entry.observation_id == trace.observation_id and
               entry.feature == bundle.observations[0].feature and
               entry.result == 'synthetic_smoke_only' for entry in generated_trace.trace):
        raise ValueError('the source feature is not illustrated in this generated app')

    for case in plan.cases:
        if case.relationship == 'source_feature_illustration' and (
                case.source_observation_id != trace.observation_id or
                case.feature != bundle.observations[0].feature):
            raise ValueError('attempt to attribute an unrelated synthetic route to source behavior')
        expected_status, ids = _expected_from_fixture(case, demo)
        if case.expected_status != expected_status or case.expected_ids != ids:
            raise ValueError(f'fixture expectation mismatch: {case.id}')

    source_file = _safe_file(Path(preview_root), 'app/main.py')
    if source_file.read_text(encoding='utf-8') != APP:
        raise ValueError('untrusted application template')
    loader = importlib.util.spec_from_file_location('_astra_feature_acceptance_app', source_file)
    if loader is None or loader.loader is None:
        raise ValueError('unable to load checked synthetic application')
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix='astra-feature-') as folder:
        with TestClient(module.create_app(Path(folder) / 'independent.sqlite3')) as client:
            for case in plan.cases:
                route, params = _endpoint(case)
                response = client.get(route, params=params)
                if response.status_code != case.expected_status:
                    raise ValueError(f'API status mismatch: {case.id}')
                if response.status_code == 200:
                    data = response.json()
                    ids = ([data['id']] if case.feature is Feature.DETAIL else
                           [row['id'] for row in data['items']])
                    if ids != case.expected_ids:
                        raise ValueError(f'API item results differ: {case.id}')
                    if case.feature is not Feature.DETAIL and data.get('synthetic') is not True:
                        raise ValueError('API response not marked synthetic')

    return FeatureAcceptanceResult(
        plan_sha256=fingerprint(plan), source_observation_id=trace.observation_id,
        pipeline_report_sha256=fingerprint(report),
        synthetic_cases_passed=len(plan.cases),
        source_illustrations_passed=sum(c.relationship == 'source_feature_illustration' for c in plan.cases),
        fixture_only_cases_passed=sum(c.relationship == 'independent_synthetic_fixture' for c in plan.cases),
        cases=[c.id for c in plan.cases],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Fixture-only acceptance adapter, never original-site proof')
    for key in ('observation', 'evidence_root', 'generated_temp_dir', 'acceptance_plan'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        plan = FeatureAcceptancePlan.model_validate_json(args.acceptance_plan.read_text(encoding='utf-8'))
        result = run_feature_acceptance(bundle, args.evidence_root, args.generated_temp_dir, plan)
    except (OSError, ValueError, ValidationError, TypeError, RuntimeError, ImportError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
