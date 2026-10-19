"""Bind pinned OWID observation proof to an offline synthetic mapping review only."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from astra_contracts.chart_table_transition_skill import (
    PROOF_ARTIFACT, PROOF_RUN, PROOF_ZIP_SHA256, SOURCE_URL,
    review_pinned_artifact,
)
from astra_contracts.synthetic_timeseries_review import review


def combined_review(archive: Path, synthetic_fixture: dict) -> dict:
    """The archive must be byte-identical to the pinned capture; never grant approval."""
    proof = review_pinned_artifact(archive)
    if (proof.get('archive_sha256') != PROOF_ZIP_SHA256
            or proof.get('github_run_id') != PROOF_RUN
            or proof.get('github_artifact_id') != PROOF_ARTIFACT
            or proof.get('source_url') != SOURCE_URL
            or proof.get('generation_contract') != 'blocked_pending_review'
            or proof.get('operator_review_approved') is not False
            or proof.get('code_generation_authorized') is not False
            or proof.get('owner_schema_connected') is not False):
        raise ValueError('pinned proof state mismatch')
    mapping = review(synthetic_fixture)
    return {'status': 'review_only', 'skill_id': 'chart_table_mode_switch',
            'proof_archive_sha256': PROOF_ZIP_SHA256,
            'proof_run_id': PROOF_RUN, 'proof_artifact_id': PROOF_ARTIFACT,
            'proof_source_url': SOURCE_URL,
            'proof_observation_id': proof['observation_id'],
            'synthetic_mapping': mapping,
            'owner_schema_connected': False, 'source_formulas_verified': False,
            'semantic_approval_verified': False, 'code_generation_authorized': False,
            'deployment_authorized': False,
            'generation_contract': 'blocked_pending_review'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline pinned evidence + synthetic mapping review')
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = combined_review(args.archive, json.loads(args.fixture.read_text(encoding='utf-8')))
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
