"""ASTRA Step 4-B: read-only, review-gated evidence -> functional spec draft.

Usage: python -m astra_contracts.functional_spec fixtures/jp_nail_brand_filter_observation_20261018.json

This is NOT code generation, DB/API inference, a browser inspector, or an approval API.
The output is stdout only, so nothing is silently created or overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from astra_contracts.observation import Certainty, EvidenceKind, Feature, ObservationBundle


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceQuality(str, Enum):
    ARCHIVED_SECONDARY = "archived_secondary"
    REPORTED_DIRECT = "reported_direct_not_independently_verified"


class FieldChange(ClosedModel):
    field: str
    before: str | int | float | bool | None
    after: str | int | float | bool | None


class EvidenceLink(ClosedModel):
    id: str
    kind: EvidenceKind
    source_ref: str


class CandidateFeature(ClosedModel):
    observation_id: str
    feature: Feature
    title: str
    claim: str
    recorded_action: str | None = None
    changed_fields: list[FieldChange]
    evidence: list[EvidenceLink] = Field(min_length=1)
    evidence_quality: SourceQuality
    review_status: str = "requires_review"


class UnresolvedItem(ClosedModel):
    observation_id: str
    feature: Feature
    claim: str
    mentioned_fields: list[str]
    reason: str  # unknown vs inferred; neither licenses implementation


class ApprovalGate(ClosedModel):
    key: str
    status: str = "pending"
    rationale: str


class FunctionalSpecDraft(ClosedModel):
    schema_version: str = "0.1"
    source_schema_version: str
    site_url: str
    source_sha256: str
    provenance: str = "observation_bundle_only"
    status: str = "draft_requires_review"
    implementation_ready: bool = False
    db_api_mapping_status: str = "not_started"
    candidate_features: list[CandidateFeature]
    unresolved: list[UnresolvedItem]
    approval_gates: list[ApprovalGate]

    @model_validator(mode="after")
    def never_approved_by_generation(self) -> "FunctionalSpecDraft":
        if (self.implementation_ready or self.status != "draft_requires_review"
                or self.db_api_mapping_status != "not_started"
                or any(x.review_status != "requires_review" for x in self.candidate_features)
                or any(x.status != "pending" for x in self.approval_gates)):
            raise ValueError("automatic specification generation cannot grant approval")
        return self


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[FieldChange]:
    """Only comparable before/after keys; one-sided fields are not event assertions."""
    return [FieldChange(field=k, before=before[k], after=after[k])
            for k in sorted(before.keys() & after.keys())
            if type(before[k]) is not type(after[k]) or before[k] != after[k]]


def derive_spec(bundle: ObservationBundle) -> FunctionalSpecDraft:
    """Pure transformation. Unconfirmed statements cannot become feature candidates."""
    validated = ObservationBundle.model_validate(bundle.model_dump(mode="json"))
    evidence_by_id = {e.id: e for e in validated.evidence}
    encoded = json.dumps(validated.model_dump(mode="json"), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    candidates: list[CandidateFeature] = []
    unresolved: list[UnresolvedItem] = []
    for ob in validated.observations:
        if ob.certainty is Certainty.OBSERVED:
            refs = [evidence_by_id[eid] for eid in ob.evidence_ids]
            secondary = all(e.kind is EvidenceKind.ARCHIVED_REPORT for e in refs)
            candidates.append(CandidateFeature(
                observation_id=ob.id, feature=ob.feature, title=ob.title,
                claim=ob.claim, recorded_action=ob.action,
                changed_fields=_changed_fields(ob.before, ob.after),
                evidence=[EvidenceLink(id=e.id, kind=e.kind, source_ref=e.source_ref) for e in refs],
                evidence_quality=(SourceQuality.ARCHIVED_SECONDARY if secondary
                                  else SourceQuality.REPORTED_DIRECT),
            ))
        else:
            unresolved.append(UnresolvedItem(
                observation_id=ob.id, feature=ob.feature, claim=ob.claim,
                mentioned_fields=sorted(set(ob.before) | set(ob.after)),
                reason=ob.certainty.value,
            ))

    gates = [
        ApprovalGate(key="confirm_behavior", rationale="A reviewer must approve observations as intended target behavior."),
        ApprovalGate(key="approve_db_api_mapping", rationale="No user schema/API contract is supplied or modified by this step."),
        ApprovalGate(key="authorize_external_or_write_actions", rationale="Any live connection, mutation or deployment requires separate approval."),
    ]
    if any(x.feature is Feature.BASIC_AGGREGATE for x in candidates + unresolved):
        gates.append(ApprovalGate(key="confirm_metric_formulas", rationale="Observed UI numbers do not establish original calculations."))
    return FunctionalSpecDraft(
        source_schema_version=validated.schema_version,
        site_url=validated.site_url, source_sha256=digest,
        candidate_features=candidates, unresolved=unresolved, approval_gates=gates,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an unapproved functional specification draft from validated UI observations")
    parser.add_argument("input", type=Path, help="Existing ObservationBundle JSON; output goes to stdout")
    args = parser.parse_args(argv)
    try:
        bundle = ObservationBundle.model_validate_json(args.input.read_text(encoding="utf-8"))
        spec = derive_spec(bundle)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f"FAIL: cannot derive spec: {exc}", file=sys.stderr)
        return 1
    print(spec.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
