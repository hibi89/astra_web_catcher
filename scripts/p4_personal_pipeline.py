"""Offline ASTRA personal-use pipeline: observation -> draft -> diagnostics -> synthetic preview.

No URL fetching, customer data, approvals, or deployment. The preview is fictional.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from pydantic import ValidationError

from astra_contracts.observation import ObservationBundle
from astra_contracts.functional_spec import derive_spec
from astra_contracts.data_mapping import OwnedSchemaDeclaration, compare_mappings
from astra_contracts.generation_contract import GenerationRequest, preflight_contract
from astra_contracts.synthetic_generator import SyntheticDemo
from astra_contracts.synthetic_bridge import bridge_trace, generate_bridge_preview


def plan(observation: Path, schema_path: Path, request_path: Path, demo_path: Path):
    bundle = ObservationBundle.model_validate_json(observation.read_text(encoding="utf-8"))
    schema = OwnedSchemaDeclaration.model_validate_json(schema_path.read_text(encoding="utf-8"))
    request = GenerationRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    demo = SyntheticDemo.model_validate_json(demo_path.read_text(encoding="utf-8"))
    spec = derive_spec(bundle)
    report = compare_mappings(spec, schema)
    contract = preflight_contract(spec, schema, report, request)
    trace = bridge_trace(spec, schema, report, request, contract, demo)
    return spec, schema, report, request, contract, demo, trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic-only personal MVP pipeline")
    parser.add_argument("--observation", type=Path, default=Path("fixtures/jp_nail_brand_filter_observation_20261018.json"))
    parser.add_argument("--schema", type=Path, default=Path("fixtures/synthetic_owned_schema_mapping_20261018.json"))
    parser.add_argument("--request", type=Path, default=Path("fixtures/synthetic_generation_request_20261018.json"))
    parser.add_argument("--demo", type=Path, default=Path("fixtures/synthetic_demo_catalog_20261018.json"))
    parser.add_argument("--generate", action="store_true", help="Write a fictional demo to a fresh system temporary folder")
    args = parser.parse_args(argv)
    try:
        spec, schema, report, request, contract, demo, trace = plan(
            args.observation, args.schema, args.request, args.demo
        )
        destination = None
        if args.generate:
            root = Path(tempfile.mkdtemp(prefix="astra-synth-"))
            generate_bridge_preview(spec, schema, report, request, contract, demo, root)
            destination = str(root)
        summary = {
            "mode": "synthetic_preview_only",
            "generation_contract": contract.status,
            "candidate_features": len(spec.candidate_features),
            "unresolved": len(spec.unresolved),
            "mapping_discrepancies": trace.mapping_discrepancy_count,
            "simulated_features": sum(x.result == "synthetic_smoke_only" for x in trace.trace),
            "original_behavior_verified": False,
            "customer_database_accessed": False,
            "preview_folder": destination,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, ValidationError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
