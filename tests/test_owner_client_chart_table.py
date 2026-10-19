"""Contract tests for the client-rendered synthetic owner Chart/Table path."""
from __future__ import annotations

import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest

from astra_contracts.synthetic_owner_isolation import COOKIE, create_owner_like_app
from astra_contracts.synthetic_sqlite_dashboard import _digest

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / 'examples/p4_owner_demo_schema.json'
ROWS_PATH = ROOT / 'examples/p4_owner_demo_rows.json'


def fixture_data():
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8')), json.loads(ROWS_PATH.read_text(encoding='utf-8'))


@pytest.fixture()
def demo():
    schema, rows = fixture_data()
    app = create_owner_like_app(schema, rows)
    with TestClient(app) as client:
        alpha = app.state.demo_sessions.issue_for_local_test('demo_alpha')
        beta = app.state.demo_sessions.issue_for_local_test('demo_beta')
        yield client, app, alpha, beta, schema, rows


def get_as(client, token, path):
    return client.get(path, headers={'Cookie': f'{COOKIE}={token}'})


def test_client_preview_is_a_data_free_owner_scoped_shell(demo):
    client, _, alpha, beta, _, _ = demo
    a = get_as(client, alpha, '/client-preview')
    b = get_as(client, beta, '/client-preview')
    assert a.status_code == b.status_code == 200
    for response, owner, forbidden in (
        (a, 'demo_alpha', 'BETA_CANARY'),
        (b, 'demo_beta', 'ALPHA_CANARY'),
    ):
        assert f'name="astra-expected-owner" content="{owner}"' in response.text
        assert 'name="astra-expected-count" content="3"' in response.text
        assert re.search(r'name="astra-expected-sha256" content="[a-f0-9]{64}"', response.text)
        assert forbidden not in response.text
        assert 'SharedDesign' not in response.text
        assert '<tbody id="table-body"></tbody>' in response.text
        assert '<g id="chart-points"></g>' in response.text
        assert 'src="/client-assets/owner-client-chart-table.js"' in response.text
    assert a.headers['cache-control'] == 'no-store'
    assert b.headers['cache-control'] == 'no-store'
    assert "script-src 'self'" in a.headers['content-security-policy']
    assert "connect-src 'self'" in a.headers['content-security-policy']


def test_client_api_hash_and_bootstrap_snapshot_match_without_server_rendering(demo):
    client, _, alpha, beta, _, _ = demo
    for token, expected_owner in ((alpha, 'demo_alpha'), (beta, 'demo_beta')):
        shell = get_as(client, token, '/client-preview').text
        payload = get_as(client, token, '/api/demo/series').json()
        digest = re.search(r'name="astra-expected-sha256" content="([a-f0-9]{64})"', shell).group(1)
        assert payload['owner_scope'] == expected_owner
        assert payload['snapshot_sha256'] == digest == _digest(payload['rows'])
        assert 'BETA_CANARY' not in shell if expected_owner == 'demo_alpha' else 'ALPHA_CANARY' not in shell


def test_client_preview_and_api_keep_the_existing_session_owner_boundary(demo):
    client, _, alpha, beta, _, _ = demo
    assert client.get('/client-preview').status_code == 401
    assert client.get('/api/demo/series').status_code == 401
    assert get_as(client, alpha, '/client-preview?owner_id=demo_beta').status_code == 400
    assert get_as(client, alpha, '/api/demo/series?owner_id=demo_beta').status_code == 400
    forged = client.get('/client-preview', headers={
        'Cookie': f'{COOKIE}={alpha}', 'X-Owner-ID': 'demo_beta',
    })
    assert forged.status_code == 200
    assert 'astra-expected-owner" content="demo_alpha' in forged.text
    assert 'BETA_CANARY' not in forged.text
    assert get_as(client, alpha, '/api/demo/owners/demo_beta/series').status_code == 404


def test_client_javascript_is_same_origin_and_uses_text_nodes_for_dynamic_content(demo):
    client, _, _, _, _, _ = demo
    response = client.get('/client-assets/owner-client-chart-table.js')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/javascript')
    assert 'fetch(\'/api/demo/series\'' in response.text
    assert 'textContent' in response.text
    assert 'innerHTML' not in response.text
    assert 'insertAdjacentHTML' not in response.text


def test_client_empty_state_is_representable_for_an_owner_with_no_rows():
    schema, rows = fixture_data()
    schema['owner_ids'].append('demo_empty')
    app = create_owner_like_app(schema, rows, allow_empty_owner=True)
    with TestClient(app) as client:
        token = app.state.demo_sessions.issue_for_local_test('demo_empty')
        shell = get_as(client, token, '/client-preview')
        payload = get_as(client, token, '/api/demo/series').json()
        assert shell.status_code == 200
        assert 'name="astra-expected-count" content="0"' in shell.text
        assert 'name="astra-expected-sha256" content="' + _digest([]) + '"' in shell.text
        assert payload['owner_scope'] == 'demo_empty'
        assert payload['count'] == 0 and payload['rows'] == []
        assert payload['snapshot_sha256'] == _digest([])


def test_empty_owner_remains_rejected_by_default_for_existing_isolation_fixture():
    schema, rows = fixture_data()
    schema['owner_ids'].append('demo_empty')
    with pytest.raises(ValueError, match='every declared demo owner needs rows'):
        create_owner_like_app(schema, rows)


def test_client_shell_rejects_untrusted_schema_metadata():
    schema, rows = fixture_data()
    schema['dataset_id'] = 'demo"><img src=x onerror=alert(1)>'
    with pytest.raises(ValueError, match='invalid dataset identifier'):
        create_owner_like_app(schema, rows)
