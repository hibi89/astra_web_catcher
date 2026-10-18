"""Regression for ASTRA's strictly synthetic observation-to-preview bridge."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration, MappingReport, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import GenerationRequest, GenerationContract, preflight_contract
from astra_contracts.synthetic_generator import SyntheticDemo
from astra_contracts.synthetic_bridge import bridge_trace, generate_bridge_preview, main

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'fixtures'
NAMES = {
    'spec': 'jp_nail_functional_spec_draft_20261018.json',
    'schema': 'synthetic_owned_schema_mapping_20261018.json',
    'report': 'synthetic_mapping_report_20261018.json',
    'contract': 'synthetic_generation_contract_20261018.json',
    'request': 'synthetic_generation_request_20261018.json',
    'demo': 'synthetic_demo_catalog_20261018.json',
}
MODELS = {
    'spec': FunctionalSpecDraft,
    'schema': OwnedSchemaDeclaration,
    'report': MappingReport,
    'contract': GenerationContract,
    'request': GenerationRequest,
    'demo': SyntheticDemo,
}


def case(**changes):
    models = {k: model.model_validate_json((FIX / NAMES[k]).read_text(encoding='utf-8'))
              for k, model in MODELS.items()}
    models.update(changes)
    return models


def run(*, inputs=None):
    return bridge_trace(**(inputs or case()))


def test_observed_filter_only_simulated_and_no_original_metrics():
    result = run()
    assert result.mode == 'synthetic_preview_only'
    assert result.preflight_status == 'blocked_pending_review'
    assert result.real_code_generation_authorized is False
    assert result.original_db_accessed is False
    assert result.user_schema_mapping_approved is False
    assert result.production_ready is False
    assert len(result.trace) == 1
    entry = result.trace[0]
    assert entry.observation_id == 'brand_all_vs_ohora'
    assert entry.feature.value == 'filter'
    assert entry.result == 'synthetic_smoke_only'
    assert entry.example_route == '/api/items?category=%EC%83%89%EC%83%81'
    assert entry.original_behavior_verified is False
    assert result.unresolved_observation_ids == ['filter_execution_unknown', 'ratio_formula_unknown']
    assert result.mapping_discrepancy_count == 7
    assert 'archived_evidence_requires_reverification' in result.preflight_block_reasons


def test_no_original_website_or_original_ui_values_in_trace():
    payload = run().model_dump_json()
    for forbidden in ('daily-dashboard-', 'OHORA', '153', '194', 'observation_bundle_only'):
        assert forbidden not in payload


def test_bridge_is_pure_and_deterministic():
    a = run().model_dump_json()
    b = run().model_dump_json()
    assert a == b
    assert len(run().synthetic_fixture_sha256) == 64
    assert len(run().functional_spec_sha256) == 64


def test_bridged_app_generated_and_its_own_tests_pass():
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        written = generate_bridge_preview(**case(), destination=Path(folder))
        assert len(written) == 8
        assert all(path.is_file() for path in written)
        trace = json.loads((Path(folder) / 'data' / 'astra_preview_trace.json').read_text(encoding='utf-8'))
        assert trace['preflight_status'] == 'blocked_pending_review'
        assert trace['original_db_accessed'] is False
        assert (Path(folder) / 'app' / 'main.py').is_file()
        assert 'OHORA' not in (Path(folder) / 'data' / 'seed.json').read_text(encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_app.py'],
                       cwd=folder, check=True, text=True, capture_output=True, timeout=30)


def test_existing_file_or_second_run_refused_without_change():
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        root = Path(folder)
        (root / 'protected.txt').write_text('do not modify', encoding='utf-8')
        with pytest.raises(ValueError, match='EMPTY'):
            generate_bridge_preview(**case(), destination=root)
        assert (root / 'protected.txt').read_text(encoding='utf-8') == 'do not modify'
        (root / 'protected.txt').unlink()
        generate_bridge_preview(**case(), destination=root)
        before = sorted(str(x.relative_to(root)) for x in root.rglob('*') if x.is_file())
        with pytest.raises(ValueError, match='EMPTY'):
            generate_bridge_preview(**case(), destination=root)
        after = sorted(str(x.relative_to(root)) for x in root.rglob('*') if x.is_file())
        assert before == after


def test_outside_temp_path_refused(tmp_path):
    with pytest.raises(ValueError, match='EMPTY'):
        generate_bridge_preview(**case(), destination=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_modified_contract_rejected_even_if_its_block_list_is_more_permissive():
    tampered = case()['contract'].model_dump(mode='json')
    tampered['block_reasons'].remove('mapping_discrepancies')
    with pytest.raises(ValueError, match='differs'):
        run(inputs=case(contract=GenerationContract.model_validate(tampered)))


def test_mismatched_functional_spec_rejected():
    altered = case()['spec'].model_dump(mode='json')
    altered['candidate_features'][0]['title'] = 'changed independently'
    with pytest.raises(ValueError, match='mapping report does not match'):
        run(inputs=case(spec=FunctionalSpecDraft.model_validate(altered)))


def test_customer_document_schema_rejected_even_with_consistent_mapping():
    cases = case()
    manifest = cases['schema'].model_dump(mode='json')
    manifest['source_kind'] = 'owner_supplied_document'
    manifest['source_label'] = 'Do not process customer schema in demo'
    schema = OwnedSchemaDeclaration.model_validate(manifest)
    report = compare_mappings(cases['spec'], schema)
    request = cases['request']
    contract = preflight_contract(cases['spec'], schema, report, request)
    with pytest.raises(ValueError, match='only synthetic'):
        run(inputs=case(schema=schema, report=report, contract=contract))


def test_nextjs_contract_rejected_for_fastapi_only_synthetic_generator():
    models = case()
    request_data = models['request'].model_dump(mode='json')
    request_data['stack'] = 'nextjs_prisma'
    request = GenerationRequest.model_validate(request_data)
    contract = preflight_contract(models['spec'], models['schema'], models['report'], request)
    with pytest.raises(ValueError, match='FastAPI'):
        run(inputs=case(request=request, contract=contract))


def test_unsupported_observed_feature_is_not_falsely_marked_simulated():
    models = case()
    spec_data = models['spec'].model_dump(mode='json')
    spec_data['candidate_features'][0]['feature'] = 'basic_aggregate'
    spec = FunctionalSpecDraft.model_validate(spec_data)
    fresh = compare_mappings(spec, models['schema'])
    contract = preflight_contract(spec, models['schema'], fresh, models['request'])
    result = run(inputs=case(spec=spec, report=fresh, contract=contract))
    assert result.trace[0].result == 'not_simulated'
    assert result.trace[0].example_route is None


def test_unobserved_claims_never_become_preview_routes():
    result = run()
    observed = {x.observation_id for x in result.trace}
    assert observed == {'brand_all_vs_ohora'}
    assert observed.isdisjoint(result.unresolved_observation_ids)


def test_no_observed_candidates_does_not_claim_coverage():
    models = case()
    spec_data = models['spec'].model_dump(mode='json')
    spec_data['candidate_features'] = []
    spec = FunctionalSpecDraft.model_validate(spec_data)
    schema_data = models['schema'].model_dump(mode='json')
    schema_data['bindings'] = []
    schema = OwnedSchemaDeclaration.model_validate(schema_data)
    report = compare_mappings(spec, schema)
    contract = preflight_contract(spec, schema, report, models['request'])
    result = run(inputs=case(spec=spec, schema=schema, report=report, contract=contract))
    assert result.trace == []
    assert 'no_observed_feature_candidates' in result.preflight_block_reasons


def test_approval_forgery_cannot_be_imported():
    data = case()['contract'].model_dump(mode='json')
    data['approval_verified'] = True
    with pytest.raises(ValidationError):
        GenerationContract.model_validate(data)


def test_cli_success_writes_only_eight_files(capsys):
    paths = [str(FIX / NAMES[x]) for x in
             ('spec', 'schema', 'report', 'contract', 'request', 'demo')]
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        assert main(paths + [folder]) == 0
        answer = capsys.readouterr()
        assert answer.err == ''
        assert json.loads(answer.out)['files_created'] == 8
        assert len([x for x in Path(folder).rglob('*') if x.is_file()]) == 8


def test_cli_rejects_nonempty_and_prints_no_success(tmp_path, capsys):
    paths = [str(FIX / NAMES[x]) for x in
             ('spec', 'schema', 'report', 'contract', 'request', 'demo')]
    assert main(paths + [str(tmp_path)]) == 1
    result = capsys.readouterr()
    assert not result.out and result.err.startswith('FAIL:')


def test_non_code_trace_contains_only_metadata():
    with tempfile.TemporaryDirectory(prefix='astra-synth-') as folder:
        generate_bridge_preview(**case(), destination=Path(folder))
        trace = (Path(folder) / 'data' / 'astra_preview_trace.json').read_text(encoding='utf-8')
        assert '<script' not in trace and 'password' not in trace
        assert 'api.github.com' not in trace
        assert 'https://' not in trace


def test_source_no_remote_database_network_or_live_stack():
    source = (ROOT / 'astra_contracts' / 'synthetic_bridge.py').read_text(encoding='utf-8')
    for banned in ('import sqlite3', 'import requests', 'urllib.request', 'subprocess.run(', 'os.system(', 'openai.'):
        assert banned not in source
