"""Regression contract tests for one archived brand-filter observation case."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.observation import ObservationBundle, main

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'fixtures' / 'jp_nail_brand_filter_observation_20261018.json'
SOURCE = ROOT / 'evidence' / 'jp_nail_brand_filter_source_20261018.md'


def read():
    return json.loads(OBS.read_text(encoding='utf-8'))


def test_real_archived_record_validates_and_source_exists():
    b = ObservationBundle.model_validate(read())
    assert len(b.evidence) == 1 and len(b.observations) == 3
    assert b.evidence[0].kind.value == 'archived_report'
    assert b.evidence[0].source_ref == str(SOURCE.relative_to(ROOT))
    assert SOURCE.is_file()
    content = SOURCE.read_text(encoding='utf-8')
    assert 'b9d676e0e7ba8af2124a0785e8c57b9ab6195f1b' in content
    assert 'actual screenshots were not retrieved' in content


def test_values_preserve_historic_screen_states():
    ob = ObservationBundle.model_validate(read()).observations[0]
    assert ob.certainty.value == 'observed' and ob.action is None
    assert ob.before['selected_brand'] == 'ALL'
    assert ob.after['selected_brand'] == 'OHORA'
    assert ob.before['analyzed_posts'] == 153 and ob.after['analyzed_posts'] == 79
    assert ob.before['collected_posts'] == 194 and ob.after['collected_posts'] == 94
    assert ob.before['average_reactions_displayed'] == 526
    assert ob.after['average_reactions_displayed'] == 629
    assert ob.before['reels_posts'] == 101 and ob.after['reels_posts'] == 78
    assert ob.before['reported_reels_percent'] == 52 and ob.after['reported_reels_percent'] == 83
    assert ob.before['direct_application_posts'] == 71 and ob.after['direct_application_posts'] == 0
    assert ob.before['sheet_posts'] == 82 and ob.after['sheet_posts'] == 79
    assert ob.before['weekly_chart_brand_series'] == 4 and ob.after['weekly_chart_brand_series'] == 1
    assert ob.before['report_run_number'] == ob.after['report_run_number'] == 3728


def test_unverified_mechanisms_are_explicit_null_without_evidence():
    b = ObservationBundle.model_validate(read())
    for ob in b.observations[1:]:
        assert ob.certainty.value == 'unknown'
        assert ob.evidence_ids == []
        assert all(value is None for value in ob.after.values())
    assert b.observations[0].after['direct_application_posts'] == 0
    assert b.observations[1].after['filter_execution_implementation'] is None


def test_unknown_cannot_gain_evidence_by_accident():
    data = read()
    data['observations'][1]['evidence_ids'] = ['historic_brand_report']
    with pytest.raises(ValidationError):
        ObservationBundle.model_validate(data)


def test_observed_requires_archived_reference():
    data = read()
    data['observations'][0]['evidence_ids'] = []
    with pytest.raises(ValidationError):
        ObservationBundle.model_validate(data)


def test_archived_report_can_be_read_via_cli(capsys):
    assert main(['validate', str(OBS)]) == 0
    assert 'PASS: 3 observations; 1 evidence items' in capsys.readouterr().out


def test_unknown_evidence_reference_rejected():
    data = read()
    data['observations'][0]['evidence_ids'] = ['missing_report']
    with pytest.raises(ValidationError):
        ObservationBundle.model_validate(data)


def test_case_does_not_invent_original_screenshot_files():
    data = read()
    refs = [e['source_ref'] for e in data['evidence']]
    assert refs == ['evidence/jp_nail_brand_filter_source_20261018.md']
    assert all(not ref.endswith(('.png', '.har')) for ref in refs)
