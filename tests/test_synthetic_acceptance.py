"""Synthetic-only generated-app acceptance; no source-site or customer DB use."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import GenerationContract, GenerationRequest, preflight_contract
from astra_contracts.synthetic_generator import APP, HTML, SyntheticDemo
from astra_contracts.synthetic_bridge import generate_bridge_preview, synthetic_route, bridge_trace
from astra_contracts.synthetic_acceptance import (
    SyntheticAcceptanceReport, check_generated_preview, main,
)
from astra_contracts.observation import Feature

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'fixtures'
MODELS = {
    'spec': (FunctionalSpecDraft, 'jp_nail_functional_spec_draft_20261018.json'),
    'schema': (OwnedSchemaDeclaration, 'synthetic_owned_schema_mapping_20261018.json'),
    'report': (MappingReport, 'synthetic_mapping_report_20261018.json'),
    'contract': (GenerationContract, 'synthetic_generation_contract_20261018.json'),
    'request': (GenerationRequest, 'synthetic_generation_request_20261018.json'),
    'demo': (SyntheticDemo, 'synthetic_demo_catalog_20261018.json'),
}


def models():
    return {k: cls.model_validate_json((FIX / path).read_text(encoding='utf-8'))
            for k, (cls, path) in MODELS.items()}


def preview():
    return tempfile.TemporaryDirectory(prefix='astra-synth-')


def build(folder: str, **updates):
    data = models()
    data.update(updates)
    generate_bridge_preview(**data, destination=Path(folder))
    return data


def test_full_bridge_to_acceptance_with_actual_generated_app_and_db():
    with preview() as folder:
        build(folder)
        report = check_generated_preview(Path(folder))
        assert report.status == 'synthetic_only_passed'
        assert report.features_exercised == ['list', 'filter', 'search', 'detail']
        assert len(report.checks) == 12
        assert report.observed_trace_ids_checked == ['brand_all_vs_ohora']
        assert report.unverified_observation_ids == ['filter_execution_unknown', 'ratio_formula_unknown']
        assert report.production_ready is False
        assert report.original_behavior_verified is False
        assert report.user_database_accessed is False


def test_observed_feature_trace_route_uses_real_synthetic_category():
    data = models()
    trace = bridge_trace(**data)
    category = data['demo'].items[0].category
    assert trace.trace[0].example_route == synthetic_route(Feature.FILTER, data['demo'])
    assert parse_qs(urlsplit(trace.trace[0].example_route).query)['category'] == [category]
    assert 'category=sample' not in trace.trace[0].example_route


def test_all_supported_synthetic_routes_use_real_fixture_values():
    d = models()['demo']
    assert synthetic_route(Feature.LIST, d) == '/api/items'
    assert parse_qs(urlsplit(synthetic_route(Feature.SEARCH, d)).query)['q'] == [d.items[0].title]
    assert parse_qs(urlsplit(synthetic_route(Feature.FILTER, d)).query)['category'] == [d.items[0].category]
    assert synthetic_route(Feature.DETAIL, d).endswith(d.items[0].id)
    assert synthetic_route(Feature.BASIC_AGGREGATE, d) is None
    assert synthetic_route(Feature.DELETE, d) is None


def test_tampered_generated_python_rejected_before_execute():
    with preview() as folder:
        build(folder)
        p = Path(folder) / 'app/main.py'
        p.write_text(APP + '\n# malicious or stale change\n', encoding='utf-8')
        with pytest.raises(ValueError, match='differs'):
            check_generated_preview(Path(folder))


def test_tampered_html_rejected():
    with preview() as folder:
        build(folder)
        p = Path(folder) / 'app/index.html'
        p.write_text(HTML + '<script>alert(1)</script>', encoding='utf-8')
        with pytest.raises(ValueError, match='differs'):
            check_generated_preview(Path(folder))


def test_synthetic_seed_mismatch_detected_against_trace_sha():
    with preview() as folder:
        build(folder)
        p = Path(folder) / 'data/seed.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        data['items'][0]['score'] += 1
        p.write_text(json.dumps(data), encoding='utf-8')
        with pytest.raises(ValueError, match='identity'):
            check_generated_preview(Path(folder))


def test_trace_pointing_to_nonexistent_demo_value_rejected():
    with preview() as folder:
        build(folder)
        p = Path(folder) / 'data/astra_preview_trace.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        data['trace'][0]['example_route'] = '/api/items?category=never-exists'
        p.write_text(json.dumps(data), encoding='utf-8')
        with pytest.raises(ValueError, match='route'):
            check_generated_preview(Path(folder))


def test_forged_trace_approval_cannot_load():
    with preview() as folder:
        build(folder)
        p = Path(folder) / 'data/astra_preview_trace.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        data['production_ready'] = True
        p.write_text(json.dumps(data), encoding='utf-8')
        with pytest.raises(ValidationError):
            check_generated_preview(Path(folder))


def test_missing_trace_fails_closed():
    with preview() as folder:
        build(folder)
        (Path(folder)/'data/astra_preview_trace.json').unlink()
        with pytest.raises(ValueError, match='absent'):
            check_generated_preview(Path(folder))


def test_trace_synthetic_item_changes_do_not_claim_original_site_behavior():
    with preview() as folder:
        build(folder)
        report = check_generated_preview(Path(folder))
        raw = report.model_dump_json()
        for forbidden in ('OHORA', 'daily-dashboard-', '153', '194', 'original_behavior_verified":true'):
            assert forbidden not in raw


def test_runner_rejects_paths_outside_system_temp(tmp_path):
    with pytest.raises(ValueError, match='system-temp'):
        check_generated_preview(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_reject_symlinked_preview(tmp_path):
    with preview() as folder:
        build(folder)
        link = tmp_path / 'astra-synth-symlink'
        link.symlink_to(Path(folder), target_is_directory=True)
        with pytest.raises(ValueError, match='system-temp'):
            check_generated_preview(link)


def test_reject_symlink_to_python_before_import():
    with preview() as folder:
        build(folder)
        target = Path(folder)/'app/main.py'
        source = Path(folder)/'app/hidden-copy.py'
        source.write_text(target.read_text(encoding='utf-8'), encoding='utf-8')
        target.unlink()
        target.symlink_to(source)
        with pytest.raises(ValueError, match='symlink'):
            check_generated_preview(Path(folder))


def test_report_flags_are_literals_false_not_mutable_metadata():
    with preview() as folder:
        build(folder)
        original = check_generated_preview(Path(folder)).model_dump(mode='json')
        for field in ('original_behavior_verified', 'production_ready', 'user_database_accessed', 'original_generation_approved'):
            altered = dict(original)
            altered[field] = True
            with pytest.raises(ValidationError):
                SyntheticAcceptanceReport.model_validate(altered)


def test_cli_success_returns_valid_json(capsys):
    with preview() as folder:
        build(folder)
        assert main([folder]) == 0
        out = capsys.readouterr()
        assert out.err == ''
        report = SyntheticAcceptanceReport.model_validate_json(out.out)
        assert report.status == 'synthetic_only_passed'
        assert 'synthetic_list_exact' in report.checks


def test_cli_failure_has_nonzero_exit_and_no_false_success(capsys, tmp_path):
    assert main([str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert out.out == '' and out.err.startswith('FAIL:')


def test_second_synthetic_data_domain_in_same_preflight_is_verified():
    data = models()
    changed = data['demo'].model_dump(mode='json')
    changed['title'] = 'Fictional Jobs'
    changed['items'] = [
        {'id': 'python-role', 'title': 'Python Engineer', 'category': 'Engineering', 'score': 30},
        {'id': 'product-role', 'title': 'Product Designer', 'category': 'Design', 'score': 20},
    ]
    data['demo'] = SyntheticDemo.model_validate(changed)
    with preview() as folder:
        build(folder, **data)
        report = check_generated_preview(Path(folder))
        assert report.status == 'synthetic_only_passed'
        assert 'trace_route_brand_all_vs_ohora' in report.checks
        assert report.production_ready is False


def test_source_contains_no_external_network_or_db_client():
    src = (ROOT/'astra_contracts/synthetic_acceptance.py').read_text(encoding='utf-8')
    for forbidden in ('import requests', 'import socket', 'urllib.request', 'subprocess.run', 'openai', 'create_engine('):
        assert forbidden not in src
