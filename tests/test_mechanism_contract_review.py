"""Synthetic fixture tests for static two-control contracts; no browser claims."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from astra_contracts.mechanism_contract_review import (
    Mechanism, SUPPORTED, _checked_bytes, compare_mechanisms, main,
)


def sha1blob(data: bytes):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


@pytest.fixture
def fixture_root(tmp_path):
    recipes = []
    for original in SUPPORTED:
        raw = ('synthetic file for ' + original.key).encode()
        source = tmp_path / original.source
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(raw)
        evidences = []
        for i, (name, _) in enumerate(original.evidence):
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            content = (f'documentation evidence: {original.key} {i}').encode()
            p.write_bytes(content)
            evidences.append((name, hashlib.sha256(content).hexdigest()))
        recipes.append(replace(original, source_blob_sha1=sha1blob(raw), evidence=tuple(evidences)))
    return tmp_path, tuple(recipes)


def test_two_distinct_review_only_controls(fixture_root):
    root, recipes = fixture_root
    before = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
    r = compare_mechanisms(root, recipes)
    after = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
    assert before == after
    assert r['control_count'] == 2 and r['review_state'] == 'review_only_no_approval'
    assert [(x['id'],x['trigger'],x['transport']) for x in r['controls']] == [
        ('checkbox','change','own_local_dom_event'),
        ('text_form','submit','own_local_http_post')]
    for entry in r['controls']:
        assert not any(entry[k] for k in ('original_site_click_verified',
            'original_site_behavior_verified','original_http_contract_verified'))
        assert entry['evidence_level'] == 'publisher_documented_not_live_verified'
    for k in ('publisher_authenticity_verified','original_site_live_interaction_verified',
              'customer_db_or_api_authorized','generation_authorized',
              'deployment_authorized','network_used','files_written'):
        assert r[k] is False
    assert r['generation_contract'] == 'blocked_pending_review'


@pytest.mark.parametrize('index', [0, 1])
def test_changed_code_blocks(fixture_root,index):
    root, recipes = fixture_root
    path = root / recipes[index].source
    path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises(ValueError, match='Git blob SHA mismatch'):
        compare_mechanisms(root, recipes)


@pytest.mark.parametrize('index', [0, 1])
def test_changed_evidence_blocks(fixture_root,index):
    root, recipes = fixture_root
    path = root / recipes[index].evidence[0][0]
    path.write_bytes(path.read_bytes()+b'x')
    with pytest.raises(ValueError, match='evidence SHA-256 mismatch'):
        compare_mechanisms(root, recipes)


def test_missing_source_blocks(fixture_root):
    root, recipes = fixture_root
    (root/recipes[1].source).unlink()
    with pytest.raises(ValueError, match='missing'):
        compare_mechanisms(root, recipes)


def test_missing_evidence_blocks(fixture_root):
    root, recipes = fixture_root
    (root/recipes[0].evidence[0][0]).unlink()
    with pytest.raises(ValueError, match='missing'):
        compare_mechanisms(root, recipes)


def test_symlink_source_blocks(fixture_root,tmp_path):
    root, recipes = fixture_root
    p = root / recipes[0].source
    target = tmp_path/'real-data'
    target.write_bytes(p.read_bytes())
    p.unlink()
    p.symlink_to(target)
    with pytest.raises(ValueError, match='symlink'):
        compare_mechanisms(root, recipes)


def test_symlink_evidence_blocks(fixture_root):
    root, recipes = fixture_root
    p = root / recipes[1].evidence[0][0]
    q = p.parent / 'real-content.txt'
    q.write_bytes(p.read_bytes())
    p.unlink()
    p.symlink_to(q)
    with pytest.raises(ValueError, match='symlink'):
        compare_mechanisms(root, recipes)


def test_extra_recipe_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='exactly two'):
        compare_mechanisms(root, recipes+(recipes[0],))


def test_same_key_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='exactly two'):
        compare_mechanisms(root, (recipes[0],replace(recipes[1], key=recipes[0].key)))


def test_fake_behavior_verified_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='provenance'):
        compare_mechanisms(root,(replace(recipes[0],behavior_evidence='live_confirmed'),recipes[1]))


def test_transport_relabel_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='distinct|relabeled'):
        compare_mechanisms(root,(replace(recipes[0],transport='own_local_dom_event'),recipes[1]))


def test_bad_sha_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='invalid fixed'):
        compare_mechanisms(root,(replace(recipes[0],source_blob_sha1='bad'), recipes[1]))


def test_nonpublisher_url_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError,match='relabeled'):
        compare_mechanisms(root,(replace(recipes[0],reference_url='http://localhost'), recipes[1]))


def test_relative_escape_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError,match='relabeled'):
        compare_mechanisms(root,(replace(recipes[0],source='../private.txt'), recipes[1]))


def test_actual_checkbox_blob_matches_remote_sha():
    source = Path(__file__).resolve().parents[1]/'astra_contracts/public_checkbox_analogue.py'
    assert sha1blob(source.read_bytes()) == SUPPORTED[1].source_blob_sha1


def test_actual_checkbox_evidence_matches_pinned_sha():
    source = Path(__file__).resolve().parents[1]/SUPPORTED[1].evidence[0][0]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SUPPORTED[1].evidence[0][1]


def test_cli_failure_does_not_emit_report(tmp_path,capsys):
    with pytest.raises(ValueError,match='missing'):
        main(['--root',str(tmp_path)])
    assert capsys.readouterr().out == ''


def test_abs_path_guard(tmp_path):
    with pytest.raises(ValueError,match='unsafe relative path'):
        _checked_bytes(tmp_path,'/etc/passwd')


def test_trigger_swapped_even_if_set_unchanged_refused(fixture_root):
    root, recipes = fixture_root
    with pytest.raises(ValueError, match='relabeled'):
        compare_mechanisms(root,(replace(recipes[0],trigger='change'),replace(recipes[1],trigger='submit')))


def test_in_root_parent_symlink_refused(fixture_root):
    root, recipes = fixture_root
    original = root/'astra_contracts'
    directory = root/'aliased-files'
    original.rename(directory)
    original.symlink_to(directory, target_is_directory=True)
    with pytest.raises(ValueError,match='symlink'):
        compare_mechanisms(root,recipes)
