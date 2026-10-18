"""Evidence contract regression tests. No browser, network or DB access needed."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.observation import ObservationBundle, main


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "observation_brand_filter.json"


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_passes_and_preserves_null_vs_zero():
    bundle = ObservationBundle.model_validate(payload())
    assert bundle.observations[0].after["analyzed_count"] == 0
    assert bundle.observations[1].after["displayed_ratio"] is None
    assert bundle.observations[1].certainty.value == "unknown"


def test_schema_is_exportable():
    schema = ObservationBundle.model_json_schema()
    assert "ObservationBundle" in schema.get("title", "")
    assert "properties" in schema and "observations" in schema["properties"]


@pytest.mark.parametrize("mutation", [
    lambda d: d["observations"][0].update(evidence_ids=[]),
    lambda d: d["observations"][0].update(evidence_ids=["not_found"]),
    lambda d: d["observations"][1].update(evidence_ids=["ev_all"]),
    lambda d: d["evidence"].append(copy.deepcopy(d["evidence"][0])),
    lambda d: d["observations"].append(copy.deepcopy(d["observations"][0])),
    lambda d: d.update(site_url="https://alice:pass@example.org/"),
    lambda d: d.update(site_url="https://example.org/?access_token=xyz"),
    lambda d: d.update(site_url="file:///tmp/a"),
    lambda d: d["evidence"][0].update(source_ref="../raw.har"),
    lambda d: d["evidence"][0].update(captured_at="2026-10-18T20:00:00"),
    lambda d: d["observations"][0]["after"].update(access_token="secret"),
    lambda d: d["observations"][0]["after"].update(raw_response={"nested": 1}),
    lambda d: d["observations"][0].update(unsupported="forbidden"),
    lambda d: d.update(schema_version="2.0"),
])
def test_reject_invalid_bundle(mutation):
    data = payload()
    mutation(data)
    with pytest.raises(ValidationError):
        ObservationBundle.model_validate(data)


def test_inference_is_not_mislabeled_as_observed():
    data = payload()
    data["observations"][0]["certainty"] = "inferred"
    data["observations"][0]["evidence_ids"] = []
    assert ObservationBundle.model_validate(data).observations[0].certainty.value == "inferred"


def test_cli_validation_and_schema(capsys, tmp_path):
    assert main(["validate", str(FIXTURE)]) == 0
    assert capsys.readouterr().out.startswith("PASS:")
    assert main(["schema"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["title"] == "ObservationBundle"
    bad = tmp_path / "bad.json"
    bad.write_text('{"bad":true}', encoding="utf-8")
    assert main(["validate", str(bad)]) == 1
    assert "FAIL:" in capsys.readouterr().err


def test_no_runtime_or_mutating_imports():
    source = (FIXTURE.parents[1] / "astra_contracts" / "observation.py").read_text(encoding="utf-8")
    for forbidden in ("requests.", "subprocess.", "sqlite3.", "uvicorn.", "openai."):
        assert forbidden not in source
