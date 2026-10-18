"""Independent temporary SQLite DB for all tests; does not touch development data."""
from __future__ import annotations
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from nail_dashboard.app import create_app
from nail_dashboard.db import seed,connection

@pytest.fixture
def setup(tmp_path):
    path=tmp_path/'isolation.db'
    assert seed(path)['posts']>=100
    with TestClient(create_app(path)) as client:
        yield client,path

def test_route_and_assets(setup):
    c,_=setup
    assert c.get('/nails').status_code==200
    assert 'app.js' in c.get('/nails').text
    assert c.get('/nails/static/app.js').status_code==200
    assert c.get('/nails/static/style.css').status_code==200
    assert c.get('/nails/health').json()['database']=='SQLite'

def test_report_refresh_read_only(setup):
    c,path=setup
    old=path.read_bytes()
    r=c.get('/api/nails/reports/latest')
    assert r.status_code==200 and '재조회' in r.json()['refresh_mode']
    assert path.read_bytes()==old  # SELECT only; no n8n, no writes

def test_fictional_sample_and_db_counts(setup):
    c,path=setup
    brands=c.get('/api/nails/brands').json()['items']
    assert len(brands)==4 and all(b['slug'] for b in brands)
    with connection(path) as con:
        post_count=con.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
        analyzed_count=con.execute('SELECT COUNT(*) FROM posts WHERE analyzed=1').fetchone()[0]
        reel_count=con.execute("SELECT COUNT(*) FROM posts WHERE medium='reel'").fetchone()[0]
    d=c.get('/api/nails/overview').json()
    assert d['summary']['collected']==post_count
    assert d['summary']['analyzed']==analyzed_count
    assert d['summary']['reels']==reel_count
    assert d['summary']['reels_share_collected']==round(100*reel_count/post_count)

def test_brand_filter_aggregation_matches_sqlite(setup):
    c,path=setup
    all_count=c.get('/api/nails/overview').json()['summary']['analyzed']
    total=0
    for slug in ['lumi','nori','mellow','pola']:
        data=c.get('/api/nails/overview',params={'brand':slug}).json()
        with connection(path) as con:
            row=con.execute('SELECT COUNT(*) FROM posts p JOIN brands b ON b.id=p.brand_id WHERE b.slug=? AND p.analyzed=1',(slug,)).fetchone()[0]
        assert data['summary']['analyzed']==row
        assert data['selected_brand']['slug']==slug
        assert len(data['weeks'])==13
        assert sum(w[slug] for w in data['weeks']) >= 0  # backend returns 13-week per-brand counts
        total+=row
    assert total==all_count

def test_brand_compare_is_global(setup):
    c,_=setup
    brands=c.get('/api/nails/brands/compare').json()['brands']
    assert len(brands)==4
    assert set(b['slug'] for b in brands)=={'lumi','nori','mellow','pola'}
    assert '데모' in c.get('/api/nails/brands/compare').json()['formula_note']
    assert any(b['four_week_index'] is not None for b in brands)

def test_tags_category_filter_and_counts(setup):
    c,_=setup
    alltags=c.get('/api/nails/tags',params={'per_page':50}).json()
    colortags=c.get('/api/nails/tags',params={'category':'color'}).json()
    assert alltags['total']==30
    assert colortags['total']==8
    assert all(x['category']=='color' for x in colortags['items'])
    scores=[x['demand_index'] for x in colortags['items'] if x['demand_index'] is not None]
    assert scores==sorted(scores,reverse=True)
    assert '원본 공식 미확인' in colortags['formula_note']

def test_tags_pagination(setup):
    c,_=setup
    page1=c.get('/api/nails/tags').json()
    page2=c.get('/api/nails/tags',params={'page':2}).json()
    assert len(page1['items'])==14 and len(page2['items'])==14
    assert page1['pages']==3 and page1['items'][0]!=page2['items'][0]
    assert c.get('/api/nails/tags',params={'category':'season'}) .json()['total']==5

def test_posts_top20_and_15_5_pages(setup):
    c,_=setup
    first=c.get('/api/nails/posts').json()
    second=c.get('/api/nails/posts',params={'page':2}).json()
    assert first['total']==second['total']==20
    assert len(first['items'])==15 and len(second['items'])==5
    assert first['page']==1 and second['page']==2
    reactions=[x['reactions'] for x in first['items']+second['items']]
    assert reactions==sorted(reactions,reverse=True)

def test_post_brand_filter_and_page_reset_contract(setup):
    c,_=setup
    previous=c.get('/api/nails/posts',params={'brand':'all','page':2}).json()
    selected=c.get('/api/nails/posts',params={'brand':'mellow','page':1}).json()
    assert previous['page']==2
    assert selected['page']==1 and len(selected['items'])==15
    assert selected['total']==20 and all(p['brand_slug']=='mellow' for p in selected['items'])
    # UI change handler resets state.page=1; contract inspected in static source separately.
    js=c.get('/nails/static/app.js').text
    assert 'state.brand=brand;state.page=1;' in js

def test_post_rank_and_null_semantics(setup):
    c,path=setup
    rows=c.get('/api/nails/posts',params={'brand':'lumi'}).json()['items']
    assert rows
    assert all(x['performance_index'] is None for x in rows)
    assert all(x['url'] is None for x in rows)  # fictional, no actual Instagram post copied
    # SQL NULL means missing rather than a 0 view count.
    with connection(path) as con:
        assert con.execute('SELECT COUNT(*) FROM posts WHERE views IS NULL').fetchone()[0]>0
        assert con.execute('SELECT COUNT(*) FROM posts WHERE views=0').fetchone()[0]==0

def test_invalid_filters_and_pages(setup):
    c,_=setup
    for route,params in [('/api/nails/overview',{'brand':'stranger'}),('/api/nails/posts',{'brand':'<script>'}),
        ('/api/nails/tags',{'category':'broken'}),('/api/nails/posts',{'page':0}),('/api/nails/tags',{'page':-2}),('/api/nails/posts',{'per_page':1000})]:
        r=c.get(route,params=params)
        assert r.status_code==422,(route,params,r.status_code)

def test_missing_db_is_service_unavailable(tmp_path):
    with TestClient(create_app(tmp_path/'missing.db')) as c:
        assert c.get('/api/nails/posts').status_code==503
        assert c.get('/nails').status_code==200

def test_seed_idempotent_and_reload(setup):
    c,path=setup
    first=c.get('/api/nails/overview').json()['summary']
    assert seed(path)['status']=='skipped_existing'
    with TestClient(create_app(path)) as other:
        assert other.get('/api/nails/overview').json()['summary']==first

def test_db_seed_unique_links_and_schema(setup):
    c,path=setup
    with connection(path) as con:
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert con.execute('SELECT COUNT(*) FROM (SELECT post_id, tag_id, COUNT(*) cnt FROM post_tags GROUP BY post_id,tag_id HAVING cnt>1)').fetchone()[0]==0
        assert con.execute('SELECT COUNT(*) FROM posts').fetchone()[0]==208

def test_formulas_do_not_claim_original(setup):
    c,_=setup
    assert '원본 수식 아님' in c.get('/api/nails/brands/compare').json()['formula_note']
    assert '원본 공식 미확인' in c.get('/api/nails/tags').json()['formula_note']
    assert '미구현' in c.get('/api/nails/posts').json()['formula_note']
