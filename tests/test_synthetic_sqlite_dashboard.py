"""Real disposable SQLite → FastAPI → chart/table preview integration checks."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from astra_contracts.synthetic_sqlite_dashboard import create_synthetic_app

SCHEMA = Path(__file__).parents[1] / 'examples/p4_chart_table_synthetic_schema.json'
ROWS = Path(__file__).parents[1] / 'examples/p4_chart_table_synthetic_rows.json'


def inputs():
    return json.loads(SCHEMA.read_text()), json.loads(ROWS.read_text())


@pytest.fixture
def local():
    schema, rows = inputs()
    app = create_synthetic_app(schema, rows)
    with TestClient(app) as client:
        yield client, app, rows


def test_real_sqlite_get_contract_and_readonly_guards(local):
    client, app, source = local
    res = client.get('/api/demo/series')
    assert res.status_code == 200 and res.headers['cache-control'] == 'no-store'
    assert res.headers['x-content-type-options'] == 'nosniff'
    payload = res.json()
    assert payload['source_kind'] == 'synthetic_fixture'
    assert payload['storage'] == 'sqlite_in_memory'
    assert payload['count'] == len(source) == 15
    assert len(payload['snapshot_sha256']) == 64
    assert payload['rows'][0]['period'] == '2026-01'
    assert sorted(payload['rows'], key=lambda r:(r['period'], r['design'])) == payload['rows']
    assert payload['mapping_approved'] is False
    assert payload['owner_schema_connected'] is False
    assert payload['generation_contract'] == 'blocked_pending_review'
    for method in ('post','put','patch','delete'):
        assert client.request(method.upper(), '/api/demo/series', json={'value':10}).status_code == 405
    assert client.get('/api/admin').status_code == 404
    assert not hasattr(app.state, 'owner_db')


def test_sqlite_is_actual_source_of_server_rendered_html(local):
    client, app, source = local
    html = client.get('/preview')
    assert html.status_code == 200 and html.headers['cache-control'] == 'no-store'
    assert html.headers['content-type'].startswith('text/html')
    assert html.text.count('<circle ') == len(source)
    assert html.text.count('<tr>') == len(source) + 1
    assert 'localhost API only' in html.text
    assert 'synthetic-snapshot-sha256' in html.text
    assert 'Local SQLite API' in html.text
    assert 'SYNTHETIC DATA' in html.text and 'REVIEW ONLY' in html.text
    assert 'Owner DB: disconnected' in html.text


def test_local_test_driver_update_changes_api_and_ui_without_http_write(local):
    client, app, original = local
    changed = copy.deepcopy(original)
    changed[0]['value'] = 666.125
    app.state.synthetic_store.replace_rows_for_local_test(changed)
    api = client.get('/api/demo/series').json()
    html = client.get('/preview').text
    assert next(row for row in api['rows'] if row['design']=='Minimal' and row['period']=='2026-01')['value'] == 666.125
    assert '<td>666.125</td>' in html
    assert '18.5' not in html
    assert len(api['rows']) == len(original)
    assert api['snapshot_sha256'] in html


def test_invalid_local_update_does_not_corrupt_previous_sqlite_snapshot(local):
    client, app, original = local
    bad = copy.deepcopy(original)
    bad[0]['value'] = float('nan')
    with pytest.raises(ValueError):
        app.state.synthetic_store.replace_rows_for_local_test(bad)
    assert client.get('/api/demo/series').json()['count'] == 15
    assert '<td>18.5</td>' in client.get('/preview').text


def test_sqlite_instances_are_isolated_and_caller_mutation_does_not_leak():
    schema, rows = inputs()
    app_a = create_synthetic_app(schema, rows)
    app_b = create_synthetic_app(schema, rows)
    schema['dataset_id'] = 'tampered_later'
    rows[0]['value'] = 999
    with TestClient(app_a) as ca, TestClient(app_b) as cb:
        assert ca.get('/api/demo/series').json()['dataset_id'] == 'original_synthetic_nail_trends'
        assert ca.get('/api/demo/series').json()['rows'][0]['value'] != 999
        updated = inputs()[1]
        updated[0]['value'] = 777
        app_a.state.synthetic_store.replace_rows_for_local_test(updated)
        a_values = [r['value'] for r in ca.get('/api/demo/series').json()['rows']]
        b_values = [r['value'] for r in cb.get('/api/demo/series').json()['rows']]
        assert 777 in a_values and 777 not in b_values
    with pytest.raises(RuntimeError, match='closed'):
        app_a.state.synthetic_store.snapshot()


def test_unsafe_owner_declaration_rejected_before_database_creation():
    schema, rows = inputs()
    schema['source_kind'] = 'owner_supplied_document'
    with pytest.raises(ValueError,match='synthetic'):
        create_synthetic_app(schema, rows)


@pytest.mark.parametrize('kind', ['bad_missing_binding','unexpected_field','duplicate_series','mixed_aggregation','too_many_rows'])
def test_bad_synthetic_inputs_fail_closed(kind):
    schema, rows = inputs()
    if kind=='bad_missing_binding':
        del schema['proposed_bindings']['time_period']
    elif kind=='unexpected_field':
        rows[0]['owner_token'] = 'never accept'
    elif kind=='duplicate_series':
        rows[1] = copy.deepcopy(rows[0])
    elif kind=='mixed_aggregation':
        rows[0]['metric_definition'] = 'unrelated'
    elif kind=='too_many_rows':
        rows *= 20
    with pytest.raises(ValueError):
        create_synthetic_app(schema, rows)


def test_sql_injection_like_entity_is_data_not_query():
    schema, rows = inputs()
    rows[0]['design'] = "' OR 1=1 --"
    with TestClient(create_synthetic_app(schema, rows)) as client:
        api = client.get('/api/demo/series').json()
        assert api['count'] == 15
        assert "' OR 1=1 --" in [r['design'] for r in api['rows']]
        assert ' OR 1=1 ' in client.get('/preview').text
        assert client.get('/api/demo/series').status_code==200


def test_html_injection_escaped_from_sqlite():
    schema, rows = inputs()
    rows[0]['design'] = '<img src=x onerror="alert(1)">'
    with TestClient(create_synthetic_app(schema, rows)) as client:
        html = client.get('/preview').text
        assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in html
        assert '<img src=x onerror=' not in html
        assert client.get('/api/demo/series').json()['count'] == 15
