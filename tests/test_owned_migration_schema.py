"""Tests for static fictional schema intake with pinned source, no live DB."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from astra_contracts import owned_migration_schema as m

ROOT = Path(__file__).resolve().parents[1]


def source():
    return (ROOT / m.RELATIVE_MIGRATION).read_bytes()


def make_root(tmp_path, raw=None):
    directory = tmp_path / 'migrations'
    directory.mkdir()
    (directory / '001_initial.sql').write_bytes(source() if raw is None else raw)
    return tmp_path


def test_exact_repository_migration_blob():
    raw = source()
    assert hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest() == m.EXPECTED_GIT_BLOB
    assert len(raw) > 3000


def test_actual_offline_sqlite_shape():
    report = m.inspect_repository_schema(ROOT)
    assert report['status'] == 'offline_static_schema_inspected_review_only'
    assert report['table_count_in_static_ddl'] == 11
    assert report['exposed_resource_count'] == 4
    assert report['excluded_resource_count'] == 7
    resources = report['declaration']['resources']
    assert [r['id'] for r in resources] == ['categories', 'products', 'companies', 'job_postings']
    assert sum(len(r['fields']) for r in resources) == 22
    assert report['declaration']['source_kind'] == 'synthetic_fixture'
    assert report['declaration']['bindings'] == []
    assert all(r['kind'] == 'db_table' for r in resources)
    assert all(f['data_type'] in ('integer','string') for r in resources for f in r['fields'])
    assert report['source_sha256'] == hashlib.sha256(source()).hexdigest()


def test_sensitive_table_names_and_content_not_exposed():
    report = m.inspect_repository_schema(ROOT)
    public_names = [r['id'] for r in report['declaration']['resources']]
    assert all(s not in public_names for s in ('users','sessions','orders','order_items',
                                                'cart_items','bookmarks','applications'))
    all_json = json.dumps(report)
    for secret_field in ('password_hash', 'token_hash','request_key'):
        assert secret_field not in all_json
    assert 'INSERT INTO' not in all_json


def test_null_and_storage_semantics_not_guessed():
    resources = {r['id']:r for r in m.inspect_repository_schema(ROOT)['declaration']['resources']}
    product = {f['name']:f for f in resources['products']['fields']}
    jobs = {f['name']:f for f in resources['job_postings']['fields']}
    assert product['id']['nullable'] is False
    assert product['stock'] == {'name':'stock','data_type':'integer','nullable':False}
    assert jobs['max_years']['nullable'] is True
    assert jobs['is_closed']['data_type'] == 'integer'  # SQLite storage, not boolean inference
    assert jobs['career_any']['data_type'] == 'integer'


def test_cannot_grant_approval():
    result = m.inspect_repository_schema(ROOT)
    for field in ('live_database_schema_verified','customer_database_accessed',
                  'original_site_behavior_verified','mapping_semantics_verified',
                  'authorization_granted','generation_authorized',
                  'deployment_authorized','external_network_used','files_written'):
        assert result[field] is False
    assert result['no_row_data_accessed'] is True
    assert result['generation_contract']=='blocked_pending_review'


def test_no_files_written_and_deterministic(tmp_path):
    source_root = make_root(tmp_path)
    before = {p.relative_to(source_root):p.read_bytes() for p in source_root.rglob('*') if p.is_file()}
    a = m.inspect_repository_schema(source_root)
    b = m.inspect_repository_schema(source_root)
    after = {p.relative_to(source_root):p.read_bytes() for p in source_root.rglob('*') if p.is_file()}
    assert before == after and a == b


@pytest.mark.parametrize('changed',[b'\n-- drift', b'\nATTACH DATABASE \'private.db\' AS x;', b'\nDROP TABLE users;', b'\nCREATE VIEW credentials AS SELECT * FROM users;'])
def test_tampered_ddl_refused_before_execution(tmp_path,changed):
    root = make_root(tmp_path, source()+changed)
    with pytest.raises(ValueError,match='pinned migration Git blob mismatch'):
        m.inspect_repository_schema(root)
    assert not (tmp_path/'private.db').exists()


def test_missing_migration_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='absent'):
        m.inspect_repository_schema(tmp_path)


def test_symlink_migration_refused(tmp_path):
    target = tmp_path / 'outside.sql'
    target.write_bytes(source())
    (tmp_path/'migrations').mkdir()
    (tmp_path/'migrations/001_initial.sql').symlink_to(target)
    with pytest.raises(ValueError,match='symlink'):
        m.inspect_repository_schema(tmp_path)


def test_symlink_parent_refused(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    (real/'001_initial.sql').write_bytes(source())
    (tmp_path/'migrations').symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        m.inspect_repository_schema(tmp_path)


def test_migration_size_limit(tmp_path):
    root = make_root(tmp_path, b'X'*32769)
    with pytest.raises(ValueError,match='too large'):
        m.inspect_repository_schema(root)


def test_unknown_storage_not_converted():
    with pytest.raises(ValueError,match='unsupported'):
        m._sqlite_type('BLOB')
    with pytest.raises(ValueError,match='unsupported'):
        m._sqlite_type('REAL')


def test_cli_json_stdout(capsys):
    assert m.main(['--repo-root',str(ROOT)]) == 0
    captured = capsys.readouterr()
    report=json.loads(captured.out)
    assert report['exposed_resource_count']==4 and captured.err==''


def test_cli_failure_no_success_output(tmp_path,capsys):
    assert m.main(['--repo-root',str(tmp_path)]) == 1
    out=capsys.readouterr()
    assert out.out == '' and 'FAIL:' in out.err


def test_existing_data_mapping_model_when_available():
    import importlib.util
    if importlib.util.find_spec('astra_contracts.data_mapping') is None:
        pytest.skip('complete branch source not mounted in isolated test workspace')
    from astra_contracts.data_mapping import OwnedSchemaDeclaration
    doc = m.inspect_repository_schema(ROOT)['declaration']
    typed = OwnedSchemaDeclaration.model_validate(doc)
    assert len(typed.resources)==4
    assert typed.source_kind=='synthetic_fixture'
    assert len(typed.bindings)==0
