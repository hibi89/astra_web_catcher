"""ASTRA: trace an unapproved UI spec to a separate, fictional runnable demo.

This adapter NEVER generates an application from the observed site's content.
It verifies the v0.1 fail-closed preflight and then delegates to the strictly
synthetic generator. The only new generated file is a non-executable trace.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, ValidationError

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import (
    GenerationContract, GenerationRequest, fingerprint, preflight_contract,
)
from astra_contracts.observation import Feature
from astra_contracts.synthetic_generator import SyntheticDemo, generate_synthetic


# The generated demo already implements these routes using *fictional rows*.
# An observed feature is only mapped to a smoke-test illustration, not reproduced.
def synthetic_route(feature: Feature, demo: SyntheticDemo) -> str | None:
    """One concrete smoke route from FICTIONAL sample rows; never from observed UI."""
    item = demo.items[0]
    if feature is Feature.LIST:
        return "/api/items"
    if feature is Feature.SEARCH:
        return "/api/items?" + urlencode({"q": item.title})
    if feature is Feature.FILTER:
        return "/api/items?" + urlencode({"category": item.category})
    if feature is Feature.DETAIL:
        return "/api/items/" + item.id
    return None



class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceEntry(ClosedModel):
    observation_id: str
    feature: Feature
    result: Literal["synthetic_smoke_only", "not_simulated"]
    example_route: str | None = None
    original_behavior_verified: Literal[False] = False


class SyntheticBridgeTrace(ClosedModel):
    version: Literal["0.1"] = "0.1"
    mode: Literal["synthetic_preview_only"] = "synthetic_preview_only"
    real_code_generation_authorized: Literal[False] = False
    original_db_accessed: Literal[False] = False
    user_schema_mapping_approved: Literal[False] = False
    production_ready: Literal[False] = False
    preflight_status: Literal["blocked_pending_review"] = "blocked_pending_review"
    preflight_block_reasons: list[str]
    functional_spec_sha256: str
    synthetic_fixture_sha256: str
    source_schema_kind: Literal["synthetic_fixture"] = "synthetic_fixture"
    unresolved_observation_ids: list[str]
    mapping_discrepancy_count: int
    trace: list[TraceEntry]


def bridge_trace(
    spec: FunctionalSpecDraft,
    schema: OwnedSchemaDeclaration,
    report: MappingReport,
    request: GenerationRequest,
    contract: GenerationContract,
    demo: SyntheticDemo,
) -> SyntheticBridgeTrace:
    """Pure preflight. No file system access or network requests."""
    spec = FunctionalSpecDraft.model_validate(spec.model_dump(mode="json"))
    schema = OwnedSchemaDeclaration.model_validate(schema.model_dump(mode="json"))
    report = MappingReport.model_validate(report.model_dump(mode="json"))
    request = GenerationRequest.model_validate(request.model_dump(mode="json"))
    contract = GenerationContract.model_validate(contract.model_dump(mode="json"))
    demo = SyntheticDemo.model_validate(demo.model_dump(mode="json"))

    if schema.source_kind != "synthetic_fixture":
        raise ValueError("only synthetic schema declarations are accepted for preview")
    if request.mode != "contract_only" or request.scope != "new_isolated_project":
        raise ValueError("unexpected source contract scope")
    if request.stack != "fastapi_sqlite":
        raise ValueError("synthetic generator supports only the FastAPI/SQLite demo")
    expected = preflight_contract(spec, schema, report, request)
    if contract.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise ValueError("preflight contract differs from freshly recomputed inputs")
    if not contract.block_reasons or "independent_generation_not_authorized" not in contract.block_reasons:
        raise ValueError("upstream generation must remain blocked")

    trace = [
        TraceEntry(
            observation_id=c.observation_id,
            feature=c.feature,
            result="synthetic_smoke_only" if synthetic_route(c.feature, demo) is not None else "not_simulated",
            example_route=synthetic_route(c.feature, demo),
        ) for c in spec.candidate_features
    ]
    return SyntheticBridgeTrace(
        preflight_block_reasons=sorted(contract.block_reasons),
        functional_spec_sha256=fingerprint(spec),
        synthetic_fixture_sha256=fingerprint(demo),
        unresolved_observation_ids=sorted({x.observation_id for x in spec.unresolved}),
        mapping_discrepancy_count=sum(
            x.status != "structurally_compatible_unapproved" for x in report.findings
        ),
        trace=trace,
    )


def generate_bridge_preview(
    spec: FunctionalSpecDraft,
    schema: OwnedSchemaDeclaration,
    report: MappingReport,
    request: GenerationRequest,
    contract: GenerationContract,
    demo: SyntheticDemo,
    destination: Path,
) -> list[Path]:
    """Write synthetic artifacts only to an empty, guarded temp folder.

    This is separate from the *blocked* production-code GenerationContract.
    The trace never contains observed UI values, user prose, or original URLs.
    """
    trace = bridge_trace(spec, schema, report, request, contract, demo)
    generated = generate_synthetic(demo, destination)
    path = Path(destination) / "data" / "astra_preview_trace.json"
    with path.open("x", encoding="utf-8") as output:
        output.write(trace.model_dump_json(indent=2) + "\n")
    return generated + [path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate only a synthetic demo with traceable UI observation coverage"
    )
    parser.add_argument("spec", type=Path)
    parser.add_argument("schema", type=Path)
    parser.add_argument("mapping_report", type=Path)
    parser.add_argument("preflight_contract", type=Path)
    parser.add_argument("generation_request", type=Path)
    parser.add_argument("synthetic_fixture", type=Path)
    parser.add_argument("empty_temp_folder", type=Path)
    args = parser.parse_args(argv)
    try:
        spec = FunctionalSpecDraft.model_validate_json(args.spec.read_text(encoding="utf-8"))
        schema = OwnedSchemaDeclaration.model_validate_json(args.schema.read_text(encoding="utf-8"))
        report = MappingReport.model_validate_json(args.mapping_report.read_text(encoding="utf-8"))
        contract = GenerationContract.model_validate_json(args.preflight_contract.read_text(encoding="utf-8"))
        request = GenerationRequest.model_validate_json(args.generation_request.read_text(encoding="utf-8"))
        demo = SyntheticDemo.model_validate_json(args.synthetic_fixture.read_text(encoding="utf-8"))
        files = generate_bridge_preview(spec, schema, report, request, contract, demo, args.empty_temp_folder)
    except (OSError, UnicodeError, ValidationError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"mode": "synthetic_preview_only", "files_created": len(files),
                      "trace_file": str(files[-1])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
