"""Owner-scoped synthetic-only SQLite → API/UI isolation and mapping fail-closed tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from astra_contracts.synthetic_owner_isolation import COOKIE, _declaration, create_owner_like_app

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / 'examples/p4_owner_demo_schema.json'
ROWS = ROOT / 'examples/p4_owner_demo_rows.json'


def inputs():
    return json.loads(SCHEMA.read_text()), json.loads(ROWS.read_text())


@pytest.fixture()
def environment():
    schema, rows = inputs()
    app = create_owner_like_app(schema, rows)
    with TestClient(app) as client:
        alpha = app.state.demo_sessions.issue_for_local_test('demo_alpha')
        beta = app.state.demo_sessions.issue_for_local_test('demo_beta')
        yield client, app, alpha, beta, schema, rows


def scoped(client, token, url='/api/demo/series', headers=None):
    return client.get(url, headers={'Cookie': f'{COOKIE}={token}', **(headers or {})})


def test_owner_role_mapping_is_strictly_review_only():
    schema, _ = inputs()
    reduced, owner_ids, owner_field, diagnostic = _declaration(schema)
    assert reduced['dataset_id'] == 'original_demo_owner_nail_index'
    assert owner_field == 'workspace_key'
    assert owner_ids == ['demo_alpha', 'demo_beta']
    assert diagnostic['missing_or_incompatible'] == []
    assert all(f['status'] == 'structurally_compatible_unapproved' for f in diagnostic['findings'].values())
    assert diagnostic['semantic_approval_verified'] is False
    assert diagnostic['generation_contract'] == 'blocked_pending_review'


def test_unauthenticated_requests_receive_no_private_rows(environment):
    client, app, alpha, beta, _, _ = environment
    for path in ('/api/demo/series', '/preview', '/api/demo/owners/demo_alpha/series'):
        assert client.get(path).status_code == 401
        assert scoped(client, 'not_a_valid_token', path).status_code == 401
    assert client.get('/api/demo/series').json()['detail'] == 'unauthenticated local synthetic demo'
    assert client.get('/docs').status_code == 404
    assert client.get('/openapi.json').status_code == 404


def test_alpha_and_beta_reuse_same_series_keys_without_data_overlap(environment):
    client, app, alpha, beta, _, _ = environment
    a, b = scoped(client, alpha), scoped(client, beta)
    assert a.status_code == b.status_code == 200
    da, db = a.json(), b.json()
    assert da['owner_scope'] == 'demo_alpha' and db['owner_scope'] == 'demo_beta'
    assert da['count'] == db['count'] == 3
    assert da['snapshot_sha256'] != db['snapshot_sha256']
    assert 'BETA_CANARY' not in json.dumps(da)
    assert 'ALPHA_CANARY' not in json.dumps(db)
    assert 10.125 in [r['invented_score'] for r in da['rows']]
    assert 90.875 in [r['invented_score'] for r in db['rows']]
    assert {x['design_label'] for x in da['rows']} == {'SharedDesign', 'ALPHA_CANARY'}
    assert {x['design_label'] for x in db['rows']} == {'SharedDesign', 'BETA_CANARY'}
    assert all(x['metric_label'] == 'synthetic_alpha_index' for x in da['rows'])
    assert all(x['metric_label'] == 'synthetic_beta_index' for x in db['rows'])
    for payload in (da, db):
        assert payload['owner_binding_status'] == 'structurally_compatible_unapproved'
        assert payload['mapping_approved'] is False
        assert payload['owner_schema_connected'] is False
        assert payload['code_generation_authorized'] is False
        assert payload['deployment_authorized'] is False
        assert payload['generation_contract'] == 'blocked_pending_review'
        assert len(payload['snapshot_sha256']) == 64
    assert a.headers['cache-control'] == b.headers['cache-control'] == 'no-store'


def test_owner_idor_route_returns_404_not_other_owners_rows(environment):
    client, app, alpha, beta, _, _ = environment
    assert scoped(client, alpha, '/api/demo/owners/demo_alpha/series').json()['count'] == 3
    assert scoped(client, beta, '/api/demo/owners/demo_beta/series').json()['count'] == 3
    assert scoped(client, alpha, '/api/demo/owners/demo_beta/series').status_code == 404
    assert scoped(client, beta, '/api/demo/owners/demo_alpha/series').status_code == 404
    assert scoped(client, alpha, '/api/demo/owners/nobody/series').status_code == 404


def test_headers_and_query_parameters_do_not_override_session_principal(environment):
    client, app, alpha, beta, _, _ = environment
    headers = {'X-Owner-ID': 'demo_beta', 'X-Forwarded-User': 'demo_beta', 'X-Session-Owner': 'demo_beta'}
    result = scoped(client, alpha, headers=headers)
    assert result.status_code == 200 and result.json()['owner_scope'] == 'demo_alpha'
    assert 'BETA_CANARY' not in result.text
    for uri in ('/api/demo/series?owner_id=demo_beta', '/preview?owner_id=demo_beta'):
        assert scoped(client, alpha, uri).status_code == 400


def test_owner_html_preview_is_scoped_and_escaped(environment):
    client, app, alpha, beta, _, _ = environment
    a = scoped(client, alpha, '/preview')
    b = scoped(client, beta, '/preview')
    assert a.status_code == b.status_code == 200
    assert 'ALPHA_CANARY' in a.text and 'BETA_CANARY' not in a.text
    assert 'BETA_CANARY' in b.text and 'ALPHA_CANARY' not in b.text
    assert '<td>10.125</td>' in a.text and '<td>90.875</td>' not in a.text
    assert '<td>90.875</td>' in b.text and '<td>10.125</td>' not in b.text
    assert a.text.count('<circle ') == b.text.count('<circle ') == 3
    assert a.text.count('<tr>') == b.text.count('<tr>') == 4
    assert scoped(client, alpha).json()['snapshot_sha256'] in a.text
    assert scoped(client, beta).json()['snapshot_sha256'] in b.text
    assert 'SYNTHETIC DATA' in a.text and 'REVIEW ONLY' in b.text
    assert "connect-src 'self'" in a.headers['content-security-policy']
    assert a.headers['cache-control'] == 'no-store'


def test_disposable_sqlite_updates_cannot_change_other_owner(environment):
    client, app, alpha, beta, _, rows = environment
    before_b = scoped(client, beta).json()['snapshot_sha256']
    updated = copy.deepcopy([x for x in rows if x['workspace_key'] == 'demo_alpha'])
    updated[0]['invented_score'] = 666.125
    app.state.demo_owner_store.replace_owner_for_local_test('demo_alpha', updated)
    assert '<td>666.125</td>' in scoped(client, alpha, '/preview').text
    assert '<td>666.125</td>' not in scoped(client, beta, '/preview').text
    assert scoped(client, beta).json()['snapshot_sha256'] == before_b
    assert scoped(client, alpha).json()['snapshot_sha256'] != before_b


def test_cross_owner_in_process_update_rejected_without_corrupting_state(environment):
    client, app, alpha, beta, _, rows = environment
    before_a = scoped(client, alpha).json()['snapshot_sha256']
    before_b = scoped(client, beta).json()['snapshot_sha256']
    malicious = copy.deepcopy([x for x in rows if x['workspace_key'] == 'demo_beta'])
    with pytest.raises(ValueError, match='owner-scoped'):
        app.state.demo_owner_store.replace_owner_for_local_test('demo_alpha', malicious)
    assert scoped(client, alpha).json()['snapshot_sha256'] == before_a
    assert scoped(client, beta).json()['snapshot_sha256'] == before_b


def test_invalid_update_rolls_back_owner_rows(environment):
    client, app, alpha, beta, _, rows = environment
    before = scoped(client, alpha).json()['snapshot_sha256']
    changed = copy.deepcopy([x for x in rows if x['workspace_key'] == 'demo_alpha'])
    changed[0]['invented_score'] = float('nan')
    with pytest.raises(ValueError):
        app.state.demo_owner_store.replace_owner_for_local_test('demo_alpha', changed)
    assert scoped(client, alpha).json()['snapshot_sha256'] == before


def test_no_public_session_issuance_or_mutation_routes(environment):
    client, app, alpha, beta, _, _ = environment
    for path in ('/api/demo/series', '/preview'):
        for method in ('POST', 'PATCH', 'PUT', 'DELETE'):
            result = client.request(method, path, headers={'Cookie': f'{COOKIE}={alpha}'}, json={'owner_id':'demo_beta'})
            assert result.status_code == 405
    assert client.post('/api/demo/sessions', json={'owner_id':'demo_beta'}).status_code == 404
    assert client.get('/api/demo/sessions').status_code == 404


def test_session_tokens_are_opaque_nonreusable_between_apps(environment):
    client, app, alpha, beta, _, _ = environment
    assert len(alpha) > 30 and alpha != beta
    assert app.state.demo_sessions.resolve(alpha) == 'demo_alpha'
    assert app.state.demo_sessions.resolve(beta) == 'demo_beta'
    assert app.state.demo_sessions.resolve(alpha + 'x') is None
    assert app.state.demo_sessions.resolve('a' * 500) is None
    with pytest.raises(ValueError):
        app.state.demo_sessions.issue_for_local_test('production_customer')
    schema, rows = inputs()
    other = create_owner_like_app(schema, rows)
    with TestClient(other) as separate:
        assert scoped(separate, alpha).status_code == 401
        assert scoped(separate, beta).status_code == 401


def test_caller_mutation_and_lifespan_closure_do_not_leak():
    schema, rows = inputs()
    app = create_owner_like_app(schema, rows)
    schema['dataset_id'] = 'tampered'
    rows[0]['invented_score'] = 999.0
    with TestClient(app) as client:
        token = app.state.demo_sessions.issue_for_local_test('demo_alpha')
        record = scoped(client, token).json()
        assert record['dataset_id'] == 'original_demo_owner_nail_index'
        assert all(item['invented_score'] != 999.0 for item in record['rows'])
    assert app.state.demo_sessions.resolve(token) is None
    with pytest.raises(RuntimeError, match='closed'):
        app.state.demo_owner_store.snapshot('demo_alpha')


def test_injected_html_and_sql_like_values_are_passive():
    schema, rows = inputs()
    rows[0]['design_label'] = '<img src=x onerror="alert(1)">'
    rows[3]['design_label'] = "' OR 1=1 --"
    app = create_owner_like_app(schema, rows)
    with TestClient(app) as client:
        t_a = app.state.demo_sessions.issue_for_local_test('demo_alpha')
        t_b = app.state.demo_sessions.issue_for_local_test('demo_beta')
        assert scoped(client, t_a).json()['count'] == 3
        assert scoped(client, t_b).json()['count'] == 3
        assert '<img src=x onerror=' not in scoped(client, t_a, '/preview').text
        assert '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in scoped(client, t_a, '/preview').text
        assert '&#x27; OR 1=1 --' in scoped(client, t_b, '/preview').text
        assert "' OR 1=1 --" not in scoped(client, t_a, '/preview').text


@pytest.mark.parametrize('case', [
    'owner_kind_boolean', 'owner_role_collision', 'owner_missing', 'owner_duplicate',
    'owner_real_identifier', 'owner_unapproved_schema', 'owner_unknown_field',
    'role_wrong_type', 'owner_binding_absent', 'owner_binding_forged',
    'extra_unused_column', 'extra_approval_flag',
])
def test_unsafe_owner_declarations_fail_closed(case):
    schema, rows = inputs()
    if case == 'owner_kind_boolean': schema['columns'][0]['kind'] = 'boolean'
    elif case == 'owner_role_collision': schema['proposed_bindings']['numeric_measure'] = 'workspace_key'
    elif case == 'owner_missing': schema['owner_ids'] = ['demo_alpha']
    elif case == 'owner_duplicate': schema['owner_ids'] = ['demo_alpha','demo_alpha']
    elif case == 'owner_real_identifier': schema['owner_ids'][0] = 'customer_12345'
    elif case == 'owner_unapproved_schema': schema['source_kind'] = 'owner_supplied_document'
    elif case == 'owner_unknown_field': schema['owner_binding'] = 'real_owner_id'
    elif case == 'role_wrong_type': schema['columns'][3]['kind'] = 'boolean'
    elif case == 'owner_binding_absent': del schema['owner_binding']
    elif case == 'owner_binding_forged': schema['owner_binding'] = {'new':'workspace_key'}
    elif case == 'extra_unused_column': schema['columns'].append({'name':'internal_secret','kind':'string'})
    elif case == 'extra_approval_flag': schema['code_generation_authorized'] = True
    with pytest.raises((ValueError, TypeError)):
        create_owner_like_app(schema, rows)


@pytest.mark.parametrize('case', [
    'foreign_owner_row', 'missing_owner_row', 'undeclared_column', 'duplicate_pair',
    'empty_owner', 'invalid_numeric', 'owner_cross_grain',
])
def test_unsafe_owner_records_fail_before_database(case):
    schema, rows = inputs()
    if case == 'foreign_owner_row': rows[0]['workspace_key'] = 'demo_charlie'
    elif case == 'missing_owner_row': rows = [r for r in rows if r['workspace_key'] == 'demo_alpha']
    elif case == 'undeclared_column': rows[0]['extra'] = 'secret'
    elif case == 'duplicate_pair': rows[1] = copy.deepcopy(rows[0])
    elif case == 'empty_owner': rows[0]['workspace_key'] = ''
    elif case == 'invalid_numeric': rows[0]['invented_score'] = 'bad'
    elif case == 'owner_cross_grain': rows[0]['observation_month'] = '2026'
    with pytest.raises((ValueError, TypeError)):
        create_owner_like_app(schema, rows)


def test_owner_order_does_not_change_backend_scope():
    schema, rows = inputs()
    reversed_data = list(reversed(rows))
    with TestClient(create_owner_like_app(schema, reversed_data)) as client:
        a = scoped(client, client.app.state.demo_sessions.issue_for_local_test('demo_alpha')).json()
        b = scoped(client, client.app.state.demo_sessions.issue_for_local_test('demo_beta')).json()
        assert a['owner_scope'] == 'demo_alpha' and b['owner_scope'] == 'demo_beta'
        assert len(a['rows']) == len(b['rows']) == 3
        assert a['snapshot_sha256'] != b['snapshot_sha256']
