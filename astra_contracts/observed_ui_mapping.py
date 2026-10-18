"""Offline observation -> explicit schema -> read-only synthetic UI traceability.

Never infer owner field names, visit reference websites, connect external databases,
create a generated application, or upgrade an operator's claim into verified truth.

CLI: python -m astra_contracts.observed_ui_mapping BUNDLE DECLARATION TABLE PLAN EVIDENCE_ROOT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.data_mapping import DataType, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import derive_spec
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import Certainty, EvidenceKind, Feature, ObservationBundle
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable

IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
HEX_SHA = r'^[0-9a-f]{64}$'


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class UIActionLink(ClosedModel):
    """Human-declared link, *not* extracted by inference from a website."""
    id: str = Field(min_length=2, max_length=64, pattern=r'^[a-z][a-z0-9_-]+$')
    observation_id: str = Field(min_length=2, max_length=64)
    ui_field: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=100)
    resource_field: str = Field(min_length=1, max_length=100)
    synthetic_preview_field: str = Field(min_length=1, max_length=64)
    requested_widget: Literal['exact_match_filter']

    @model_validator(mode='after')
    def safe_names(self):
        for field in ('ui_field', 'resource_id', 'resource_field', 'synthetic_preview_field'):
            if not IDENTIFIER.fullmatch(getattr(self, field)):
                raise ValueError(f'unsafe {field} identifier')
        return self


class UIActionMappingPlan(ClosedModel):
    version: Literal['0.1'] = '0.1'
    scope: Literal['offline_synthetic_readonly_traceability']
    observation_sha256: str = Field(pattern=HEX_SHA)
    declaration_sha256: str = Field(pattern=HEX_SHA)
    synthetic_table_sha256: str = Field(pattern=HEX_SHA)
    evidence_sha256_by_id: dict[str, str] = Field(min_length=1, max_length=50)
    links: list[UIActionLink] = Field(min_length=1, max_length=30)
    original_site_verified: Literal[False] = False
    owner_database_access_authorized: Literal[False] = False
    production_generation_authorized: Literal[False] = False
    review_approved: Literal[False] = False

    @model_validator(mode='after')
    def unique(self):
        ids = [x.id for x in self.links]
        keys = [(x.observation_id, x.ui_field) for x in self.links]
        if len(set(ids)) != len(ids) or len(set(keys)) != len(keys):
            raise ValueError('duplicate UI link id or observation+field')
        if any(not re.fullmatch(r'^[a-z][a-z0-9_-]{1,63}$', name) or
               not re.fullmatch(HEX_SHA, digest)
               for name, digest in self.evidence_sha256_by_id.items()):
            raise ValueError('invalid evidence ID or SHA-256')
        return self


class PreviewControl(ClosedModel):
    link_id: str
    observation_id: str
    ui_field: str
    declared_resource: str
    declared_field: str
    widget: Literal['exact_match_filter'] = 'exact_match_filter'
    read_only_route: Literal['/api/rows'] = '/api/rows'
    query_filter_by: str
    query_filter_value: str | int
    demo_match_count: int = Field(ge=1)
    evidence_ids: list[str]
    evidence_quality: Literal['operator_reported_not_independently_verified'] = 'operator_reported_not_independently_verified'
    synthetic_illustration_only: Literal[True] = True
    semantics_approved: Literal[False] = False


class LinkFinding(ClosedModel):
    link_id: str
    observation_id: str
    ui_field: str
    status: Literal[
        'synthetic_preview_candidate_unapproved',
        'unknown_or_inferred_observation', 'unsupported_observed_feature',
        'archived_secondary_only', 'missing_action_trace',
        'ui_field_not_observed_as_changed', 'explicit_source_binding_mismatch',
        'source_mapping_not_compatible', 'preview_field_not_declared',
        'preview_type_conflict', 'observed_value_not_in_preview',
    ]
    explanation: str


class UIActionMappingReport(ClosedModel):
    version: Literal['0.1'] = '0.1'
    status: Literal['review_only_never_authorized'] = 'review_only_never_authorized'
    observation_sha256: str
    declaration_sha256: str
    synthetic_table_sha256: str
    plan_sha256: str
    evidence_integrity_verified: Literal[True] = True
    evidence_content_authenticated: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    owner_db_accessed: Literal[False] = False
    generation_authorized: Literal[False] = False
    production_ready: Literal[False] = False
    unresolved_observation_ids: list[str]
    findings: list[LinkFinding]
    synthetic_preview_candidates: list[PreviewControl]
    required_reviews: list[str]


def _verify_local_evidence(bundle: ObservationBundle, expected: dict[str, str], root: Path) -> None:
    """Pin local evidence bytes, never treat that integrity as proof of truth."""
    evidences = {item.id: item for item in bundle.evidence}
    if set(expected) != set(evidences):
        raise ValueError('evidence digest map must cover exactly the bundle evidence IDs')
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('evidence root must be a real directory')
    root = root.resolve(strict=True)
    for evidence in evidences.values():
        relative = Path(evidence.source_ref)
        if (relative.is_absolute() or '..' in relative.parts or not relative.parts
                or any(part in ('', '.') for part in relative.parts)):
            raise ValueError('unsafe evidence path')
        location = root / relative
        # Reject any symlink, including one in an intermediate directory,
        # before following a resolved path outside the evidence root.
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('symlinked evidence is forbidden')
        if not location.resolve(strict=False).is_relative_to(root):
            raise ValueError('evidence path escapes declared root')
        if not location.is_file() or location.stat().st_size > 1024 * 1024:
            raise ValueError('evidence missing, invalid or over 1 MiB')
        if hashlib.sha256(location.read_bytes()).hexdigest() != expected[evidence.id]:
            raise ValueError(f'evidence integrity failure: {evidence.id}')


def build_ui_mapping(bundle: ObservationBundle, declaration: OwnedSchemaDeclaration,
                     table: AlternateSyntheticTable, plan: UIActionMappingPlan,
                     evidence_root: Path) -> UIActionMappingReport:
    """Deterministic, no side effects. Candidate != observed-site equivalence."""
    bundle = ObservationBundle.model_validate(bundle.model_dump(mode='json'))
    declaration = OwnedSchemaDeclaration.model_validate(declaration.model_dump(mode='json'))
    table = AlternateSyntheticTable.model_validate(table.model_dump(mode='json'))
    plan = UIActionMappingPlan.model_validate(plan.model_dump(mode='json'))
    if declaration.source_kind != 'synthetic_fixture':
        raise ValueError('owner-supplied or live schemas are out of scope')
    if (plan.observation_sha256 != fingerprint(bundle) or
        plan.declaration_sha256 != fingerprint(declaration) or
        plan.synthetic_table_sha256 != fingerprint(table)):
        raise ValueError('stale or unrelated observation, declaration or preview fixture')
    _verify_local_evidence(bundle, plan.evidence_sha256_by_id, evidence_root)

    spec = derive_spec(bundle)
    # The older comparator intentionally rejects bindings to unobserved/unchanged
    # fields. Preserve that gate for valid candidates, while letting this
    # diagnostic *report* (not crash on) links to unresolved field claims.
    candidate_keys = {(c.observation_id, f.field)
                      for c in spec.candidate_features for f in c.changed_fields}
    comparable_declaration = declaration.model_copy(update={
        'bindings': [b for b in declaration.bindings
                     if (b.observation_id, b.ui_field) in candidate_keys]})
    mapping = compare_mappings(spec, comparable_declaration)
    candidates = {c.observation_id: c for c in spec.candidate_features}
    source_observations = {o.id: o for o in bundle.observations}
    findings_by_field = {(m.observation_id, m.ui_field): m for m in mapping.findings}
    explicit_bindings = {(b.observation_id, b.ui_field): b for b in declaration.bindings}
    physical_bindings = {b.source_field: b.logical_field for b in table.bindings}

    findings = []
    preview_controls = []
    for link in plan.links:
        if link.observation_id not in source_observations:
            raise ValueError(f'link references nonexistent observation: {link.id}')
        ob = source_observations[link.observation_id]
        candidate = candidates.get(ob.id)
        finding = findings_by_field.get((ob.id, link.ui_field))
        binding = explicit_bindings.get((ob.id, link.ui_field))
        status, reason = '', ''
        if ob.certainty is not Certainty.OBSERVED:
            status, reason = 'unknown_or_inferred_observation', 'An unknown/inferred claim cannot drive any control.'
        elif ob.feature is not Feature.FILTER:
            status, reason = 'unsupported_observed_feature', 'Only observed filter selections are supported by this bounded step.'
        elif candidate and all(ev.kind is EvidenceKind.ARCHIVED_REPORT for ev in bundle.evidence
                               if ev.id in ob.evidence_ids):
            status, reason = 'archived_secondary_only', 'Archived prose alone is insufficient to drive a UI control.'
        elif not ob.action or not ob.action.strip():
            status, reason = 'missing_action_trace', 'A before/after snapshot with no action does not establish a usable control.'
        elif not finding:
            status, reason = 'ui_field_not_observed_as_changed', 'Only a before/after changed field can be linked.'
        elif (binding is None or binding.resource_id != link.resource_id or
              binding.resource_field != link.resource_field):
            status, reason = 'explicit_source_binding_mismatch', 'The selected field is not bound to the stated explicit resource field.'
        elif finding.status != 'structurally_compatible_unapproved':
            status, reason = 'source_mapping_not_compatible', f'Offline schema comparison: {finding.status}.'
        elif link.synthetic_preview_field not in physical_bindings:
            status, reason = 'preview_field_not_declared', 'The proposed preview column is not declared in the fictional table.'
        else:
            logical = physical_bindings[link.synthetic_preview_field]
            physical_type = DataType.INTEGER if logical == 'score' else DataType.STRING
            state_value = ob.after[link.ui_field]
            if finding.ui_type is not physical_type or type(state_value) is not (int if logical == 'score' else str):
                status, reason = 'preview_type_conflict', 'No implicit conversion between source UI values and fictional preview field.'
            else:
                count = sum(row[link.synthetic_preview_field] == state_value and
                            type(row[link.synthetic_preview_field]) is type(state_value)
                            for row in table.rows)
                if count == 0:
                    status, reason = 'observed_value_not_in_preview', 'No exact value match in the fictional rows; no data-value translation inferred.'
                else:
                    status, reason = 'synthetic_preview_candidate_unapproved', 'Exact fictional match only. Human semantic review is still required.'
                    preview_controls.append(PreviewControl(
                        link_id=link.id, observation_id=ob.id, ui_field=link.ui_field,
                        declared_resource=link.resource_id, declared_field=link.resource_field,
                        query_filter_by=link.synthetic_preview_field, query_filter_value=state_value,
                        demo_match_count=count, evidence_ids=list(ob.evidence_ids),
                    ))
        findings.append(LinkFinding(link_id=link.id, observation_id=ob.id, ui_field=link.ui_field,
                                    status=status, explanation=reason))
    return UIActionMappingReport(
        observation_sha256=fingerprint(bundle), declaration_sha256=fingerprint(declaration),
        synthetic_table_sha256=fingerprint(table), plan_sha256=fingerprint(plan),
        unresolved_observation_ids=mapping.unresolved_observation_ids,
        findings=findings, synthetic_preview_candidates=preview_controls,
        required_reviews=[
            'verify_actual_reference_site_action_and_visible_state',
            'confirm_semantics_of_each_source_ui_to_owner_field',
            'authenticate_evidence_contents_and_human_review',
            'authorize_any_owned_DB_or_API_connection_separately',
            'authorize_any_code_generation_or_deployment_separately',
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline evidence-to-fictional UI mapping diagnostic; never grants authority')
    for arg in ('observation', 'declaration', 'synthetic_table', 'link_plan', 'evidence_root'):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.observation.read_text(encoding='utf-8'))
        declaration = OwnedSchemaDeclaration.model_validate_json(args.declaration.read_text(encoding='utf-8'))
        table = AlternateSyntheticTable.model_validate_json(args.synthetic_table.read_text(encoding='utf-8'))
        plan = UIActionMappingPlan.model_validate_json(args.link_plan.read_text(encoding='utf-8'))
        report = build_ui_mapping(bundle, declaration, table, plan, args.evidence_root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
