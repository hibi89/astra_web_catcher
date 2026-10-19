"""Focused offline tests for the personal synthetic pipeline."""
from pathlib import Path

from scripts.p4_personal_pipeline import main, plan


def test_dry_run_returns_blocked_contract(capsys):
    assert main([]) == 0
    output = capsys.readouterr().out
    assert '"generation_contract": "blocked_pending_review"' in output
    assert '"customer_database_accessed": false' in output
    assert '"preview_folder": null' in output


def test_pipeline_keeps_approval_gates():
    spec, schema, report, request, contract, demo, trace = plan(
        Path("fixtures/jp_nail_brand_filter_observation_20261018.json"),
        Path("fixtures/synthetic_owned_schema_mapping_20261018.json"),
        Path("fixtures/synthetic_generation_request_20261018.json"),
        Path("fixtures/synthetic_demo_catalog_20261018.json"),
    )
    assert contract.status == "blocked_pending_review"
    assert schema.source_kind == "synthetic_fixture"
    assert not trace.original_db_accessed
    assert not trace.real_code_generation_authorized
    assert spec.candidate_features


def test_invalid_observation_fails_without_generation(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"invalid":true}', encoding="utf-8")
    assert main(["--observation", str(bad), "--generate"]) == 1
    assert "FAIL:" in capsys.readouterr().err
