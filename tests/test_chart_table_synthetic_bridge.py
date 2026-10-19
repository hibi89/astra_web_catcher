from pathlib import Path
import pytest

from astra_contracts.chart_table_synthetic_bridge import combined_review
from astra_contracts.synthetic_timeseries_review import review


def fixture():
    return {'source_kind': 'synthetic_fixture', 'dataset_id': 'example_series',
            'columns': [{'name': 'entity', 'kind': 'string'}, {'name': 'year', 'kind': 'string'},
                        {'name': 'value', 'kind': 'number'}, {'name': 'method', 'kind': 'string'}],
            'proposed_bindings': {'entity_identifier': 'entity', 'time_period': 'year',
                                  'numeric_measure': 'value', 'aggregation_semantics': 'method'}}


def test_missing_archive_fails_closed(tmp_path):
    with pytest.raises(ValueError):
        combined_review(tmp_path / 'missing.zip', fixture())


def test_wrong_archive_bytes_fails_closed(tmp_path):
    archive = tmp_path / 'fake.zip'
    archive.write_bytes(b'not pinned evidence')
    with pytest.raises(ValueError):
        combined_review(archive, fixture())


def test_synthetic_compatibility_is_unapproved():
    result = review(fixture())
    assert result['missing_or_incompatible'] == []
    assert result['generation_contract'] == 'blocked_pending_review'
    assert result['semantic_approval_verified'] is False


def test_bridge_real_archive_if_provided():
    archive = Path('/mnt/data/p4-owid-evidence.zip')
    if not archive.is_file():
        pytest.skip('original pinned GitHub Actions ZIP not available in test environment')
    result = combined_review(archive, fixture())
    assert result['proof_observation_id'] == 'public_table_view'
    assert result['generation_contract'] == 'blocked_pending_review'
    assert result['owner_schema_connected'] is False
