"""Optional real-archive integration test, enabled with OHORA_PRACTICE_ZIP.

Original ZIP is read only; SQLite is temporary. No user content enters the repo.
"""
import os
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from nail_practice.import_data import import_practice
from nail_practice.app import create_app

@pytest.mark.skipif(not os.getenv('OHORA_PRACTICE_ZIP'),reason='set OHORA_PRACTICE_ZIP to test actual input')
def test_real_ohora_zip(tmp_path):
    path=Path(os.environ['OHORA_PRACTICE_ZIP'])
    d=tmp_path/'real.db';stats=import_practice(path,d)
    assert (stats['accounts'],stats['posts'],stats['media'],stats['reactions_available'])==(294,1845,5953,1224)
    client=TestClient(create_app(d))
    assert client.get('/api/practice/overview').json()['stats']['reaction_missing']==621
    c=client.get('/api/practice/countries').json()['items']
    assert {x['country']:x['posts'] for x in c}=={'JP':910,'KR':485,'US':450}
    assert {x['country']:x['reaction_missing'] for x in c}=={'JP':331,'KR':193,'US':97}
    assert client.get('/api/practice/accounts?status=failed').json()['total']==8
    assert len(client.get('/api/practice/posts?country=JP&page=2').json()['items'])==5
    with sqlite3.connect(d) as db:
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert db.execute('SELECT COUNT(*) FROM posts WHERE reactions IS NULL').fetchone()[0]==621
