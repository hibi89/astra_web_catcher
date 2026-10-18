"""Reproducible independent fixture; never writes source archives or original DB."""
import csv
import io
from pathlib import Path
import sqlite3
import zipfile
import pytest
from fastapi.testclient import TestClient
from nail_practice.import_data import import_practice
from nail_practice.app import create_app


def csv_bytes(rows):
    buf=io.StringIO(newline='')
    out=csv.DictWriter(buf,fieldnames=list(rows[0]))
    out.writeheader();out.writerows(rows)
    return buf.getvalue().encode('utf-8-sig')

@pytest.fixture
def fixture(tmp_path):
    accounts=[
        dict(country='KR',account_key='KR_001',collection_status='collected',posts_available='5',followers_at_collection='100',error_code=''),
        dict(country='US',account_key='US_001',collection_status='collected',posts_available='5',followers_at_collection='0',error_code=''),
        dict(country='JP',account_key='JP_001',collection_status='failed',posts_available='0',followers_at_collection='',error_code='110')]
    posts=[]
    for i in range(24):
        code='KR' if i<20 else 'US'; key=code+'_001'; n=i+1
        post=dict(post_id=f'P{n:03}',account_key=key,country=code,
        posted_at=f'2026-10-{(i%20)+1:02}T23:00:00+0000',media_type='VIDEO' if i%2 else 'IMAGE',
        media_product_type='REELS' if i%2 else 'FEED',likes='' if i==0 else str(n*4), comments=str(i%3),
        engagement_count='' if i==0 else str(n*4+i%3),followers_at_collection='100',
        attached_media_rows='1',collected_at='2026-10-18T00:00:00+0000')
        posts.append(post)
    media=[dict(media_id=f'M{i:03}',post_id=f'P{i:03}',media_type='IMAGE',media_role='main') for i in range(1,25)]
    src=tmp_path/'source.zip'
    with zipfile.ZipFile(src,'w') as z:
        for name,rows in [('accounts_coverage.csv',accounts),('posts_flat_for_analysis.csv',posts),('media_merged.csv',media)]:z.writestr(name,csv_bytes(rows))
    db=tmp_path/'practice.db'
    output=import_practice(src,db)
    yield src,db,output

@pytest.fixture
def client(fixture):return TestClient(create_app(fixture[1]))

def test_import_totals(fixture):
    _,db,o=fixture
    assert (o['accounts'],o['posts'],o['media'],o['reactions_available'])==(3,24,24,23)
    with sqlite3.connect(db) as c:
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('SELECT likes,reactions FROM posts WHERE post_id="P001"').fetchone()==(None,None)
        assert c.execute('SELECT post_date,hour_kst FROM posts WHERE post_id="P001"').fetchone()==('2026-10-02',8)

def test_input_source_preserved(fixture):
    import hashlib
    src,db,_=fixture
    h=hashlib.sha256(src.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):import_practice(src,db)
    assert hashlib.sha256(src.read_bytes()).hexdigest()==h

def test_no_private_text_stored(fixture):
    _,db,_=fixture
    with sqlite3.connect(db) as c:
        fields=[x[1] for x in c.execute('PRAGMA table_info(posts)')]
        assert all(x not in fields for x in ['caption','username','post_url','image_url','media_url'])
        assert 'brands' not in [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]

@pytest.mark.parametrize('country,accounts,posts,valid', [('all',3,24,23),('KR',1,20,19),('US',1,4,4),('JP',1,0,0)])
def test_country_metrics(client,country,accounts,posts,valid):
    d=client.get('/api/practice/overview',params={'country':country}).json()
    assert (d['stats']['accounts'],d['stats']['posts'],d['stats']['reaction_available'])==(accounts,posts,valid)
    if country=='JP':
        assert d['stats']['reels_pct'] is None and d['stats']['avg_reactions_observed'] is None

def test_countries_compare_account_posts_distinct(client):
    v=client.get('/api/practice/countries').json()['items']
    assert [(r['country'],r['accounts'],r['posts']) for r in v]==[('KR',1,20),('US',1,4),('JP',1,0)]

def test_accounts_filters(client):
    v=client.get('/api/practice/accounts?status=failed').json()
    assert v['total']==1 and v['items'][0]['account_key']=='JP_001'
    assert client.get('/api/practice/accounts?country=KR').json()['total']==1

def test_top20_pagination_missing_excluded(client):
    p1=client.get('/api/practice/posts?page=1').json()
    p2=client.get('/api/practice/posts?page=2').json()
    assert (p1['total'],len(p1['items']),len(p2['items']))==(20,15,5)
    assert p1['excluded_missing_reactions']==1
    assert p1['items'][0]['reactions']>p2['items'][0]['reactions']
    assert len(client.get('/api/practice/posts?country=KR&page=2').json()['items'])==4
    assert client.get('/api/practice/posts?country=JP').json()['items']==[]

def test_comparison_missing_and_not_purchase(client):
    q=client.get('/api/practice/quality').json()
    assert q['reaction_missing']==1 and q['views']=='미수집' and q['design_tags']=='미분류'
    assert q['purchase_intent']=='미구현'

def test_read_only_after_queries(fixture,client):
    from hashlib import sha256
    db=fixture[1]; initial=sha256(db.read_bytes()).hexdigest()
    for _ in range(2):
        for endpoint in ['/api/practice/report','/api/practice/overview?country=KR','/api/practice/accounts?page=1','/api/practice/posts?page=2']:
            assert client.get(endpoint).status_code==200
    assert sha256(db.read_bytes()).hexdigest()==initial

def test_invalid_country_and_pages(client):
    assert client.get('/api/practice/overview?country=XX').status_code==422
    assert client.get('/api/practice/posts?page=0').status_code==422

def test_missing_db(tmp_path):
    c=TestClient(create_app(tmp_path/'absent.db'))
    assert c.get('/api/practice/report').status_code==503

def test_app_static(client):
    assert client.get('/practice').status_code==200
    js=client.get('/practice/static/app.js')
    assert js.status_code==200 and 'state.page=1' in js.text
    assert '미분류' in js.text
