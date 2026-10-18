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


# Extended independent SQL ↔ API regression scenarios (2026-10-18).
# Each case uses the existing setup fixture's distinct temp SQLite database.
from datetime import date,timedelta
from statistics import mean,median
import shutil,subprocess


def _posts_sql(path,brand='all',analyzed=False):
    with connection(path) as db:
        query='SELECT p.*,b.slug,p.likes+p.comments AS reactions FROM posts p JOIN brands b ON b.id=p.brand_id WHERE 1=1'
        params=[]
        if brand!='all':query+=' AND b.slug=?';params.append(brand)
        if analyzed:query+=' AND p.analyzed=1'
        return [dict(r) for r in db.execute(query,params)]


@pytest.mark.parametrize('brand',['all','lumi','nori','mellow','pola'])
def test_sql_crosscheck_kpis_weeks(setup,brand):
    c,path=setup
    data=c.get('/api/nails/overview',params={'brand':brand}).json()
    rows=_posts_sql(path,brand)
    a=[p for p in rows if p['analyzed']]
    s=data['summary']
    assert (s['collected'],s['analyzed'],s['reels'])==(len(rows),len(a),sum(p['medium']=='reel' for p in rows))
    assert s['reaction_average']==(round(mean(p['reactions'] for p in a),1) if a else None)
    assert s['reels_share_collected']==(round(100*s['reels']/len(rows)) if rows else None)
    assert len(data['weeks'])==13
    for week in data['weeks']:
        first=date.fromisoformat(week['week']);last=first+timedelta(days=6)
        for slug in ('lumi','nori','mellow','pola'):
            assert week[slug]==sum(p['slug']==slug and first<=date.fromisoformat(p['posted_at'])<=last for p in a)


@pytest.mark.parametrize('brand',['all','lumi','mellow'])
def test_sql_crosscheck_three_charts(setup,brand):
    c,path=setup
    data=c.get('/api/nails/overview',params={'brand':brand}).json()
    rows=_posts_sql(path,brand,True)
    hours={};formats={}
    medium={'reel':'릴스','carousel':'캐러셀','image':'단일 이미지'}
    for p in rows:
        hours.setdefault(p['hour_kst'],[]).append(p['reactions'])
        formats.setdefault(medium[p['medium']]+' · '+p['purpose'],[]).append(p['reactions'])
    assert data['hours']==[{'hour':h,'median':round(median(v),2)} for h,v in sorted(hours.items()) if 8<=h<=22]
    expected=[{'name':n,'mean':round(mean(v),1),'count':len(v)} for n,v in formats.items()]
    expected.sort(key=lambda x:(-x['mean'],x['name']))
    assert data['formats']==expected[:6]
    assert data['types']==[{'name':'직접 시술','count':sum(p['treatment']=='direct' for p in rows)},
                          {'name':'시트형','count':sum(p['treatment']=='sheet' for p in rows)}]


def test_sql_crosscheck_four_brand_comparison(setup):
    c,path=setup
    actual=c.get('/api/nails/brands/compare').json()['brands']
    assert len(actual)==4
    for b in actual:
        r=_posts_sql(path,b['slug']); a=[p for p in r if p['analyzed']]
        vals=[p['reactions'] for p in a]
        assert (b['collected'],b['analyzed'])==(len(r),len(a))
        assert b['reaction_median']==(round(median(vals),2) if vals else None)
        assert b['view_coverage']==(round(100*sum(p['views'] is not None for p in r)/len(r)) if r else None)


def test_sql_tag_join_scope_and_categories(setup):
    c,path=setup
    for category in ('technique','color','product','season','content'):
        result=c.get('/api/nails/tags',params={'category':category,'per_page':50}).json()
        with connection(path) as con:
            expected={r['name']:r['n'] for r in con.execute('''SELECT t.name, COUNT(p.id) n FROM tags t
                LEFT JOIN post_tags pt ON pt.tag_id=t.id LEFT JOIN posts p ON p.id=pt.post_id AND p.analyzed=1
                WHERE t.category=? GROUP BY t.id''',(category,))}
        assert result['total']==len(expected)
        assert {x['name']:x['posts'] for x in result['items']}==expected
    # Global demo tag table is intentionally independent of a sidebar brand choice.
    x=c.get('/api/nails/tags',params={'category':'color','brand':'mellow'}).json()
    y=c.get('/api/nails/tags',params={'category':'color'}).json()
    assert x==y and x['total']==8


def test_sql_all_brand_top_rank_and_pages(setup):
    c,path=setup
    for brand in ('all','lumi','nori','mellow','pola'):
        first=c.get('/api/nails/posts',params={'brand':brand}).json()
        second=c.get('/api/nails/posts',params={'brand':brand,'page':2}).json()
        expected=sorted(_posts_sql(path,brand,True),key=lambda p:(-p['reactions'],-p['id']))[:20]
        assert first['total']==second['total']==20
        assert (len(first['items']),len(second['items']))==(15,5)
        assert [x['id'] for x in first['items']+second['items']]==[x['id'] for x in expected]


def test_sql_mutation_recalculates_chart_and_top(setup):
    c,path=setup
    old=c.get('/api/nails/overview',params={'brand':'lumi'}).json()
    with connection(path) as con:
        row=con.execute("SELECT p.id FROM posts p JOIN brands b ON b.id=p.brand_id WHERE b.slug='lumi' AND p.analyzed=1 ORDER BY p.id LIMIT 1").fetchone()
        con.execute('UPDATE posts SET likes=likes+90000 WHERE id=?',(row['id'],));con.commit()
    new=c.get('/api/nails/overview',params={'brand':'lumi'}).json()
    assert new['summary']['reaction_average']>old['summary']['reaction_average']
    assert new['formats']!=old['formats']
    assert c.get('/api/nails/posts',params={'brand':'lumi'}).json()['items'][0]['id']==row['id']


def test_empty_posts_yields_null_ratios_and_zero_charts(setup):
    c,path=setup
    with connection(path) as con:
        con.execute('DELETE FROM post_tags');con.execute('DELETE FROM posts');con.commit()
    a=c.get('/api/nails/overview').json()
    s=a['summary']
    assert (s['collected'],s['analyzed'],s['reels'])==(0,0,0)
    assert all(s[k] is None for k in ('collection_rate','reels_share_collected','above_baseline_ratio','reaction_average'))
    assert a['formats']==a['hours']==[] and all(w['lumi']==0 for w in a['weeks'])
    assert c.get('/api/nails/posts').json()['items']==[]
    assert all(b['view_coverage'] is None for b in c.get('/api/nails/brands/compare').json()['brands'])


def test_zero_reaction_baseline_is_missing_ratio(setup):
    c,path=setup
    with connection(path) as con:
        con.execute('UPDATE posts SET likes=0,comments=0');con.commit()
    assert all(b['four_week_index'] is None for b in c.get('/api/nails/brands/compare').json()['brands'])
    assert all(t['demand_index'] is None for t in c.get('/api/nails/tags',params={'per_page':50}).json()['items'])


def test_zero_older_window_for_tags(setup):
    c,path=setup
    with connection(path) as con:
        con.execute("UPDATE posts SET posted_at='2026-10-15'");con.commit()
    tags=c.get('/api/nails/tags',params={'per_page':50}).json()['items']
    assert any(x['posts']>=3 for x in tags)
    assert all(t['trend_4v8'] is None for t in tags)


def test_missing_views_and_zero_views_are_distinct(setup):
    c,path=setup
    with connection(path) as con:
        ids=[x[0] for x in con.execute('SELECT id FROM posts WHERE analyzed=1 ORDER BY likes+comments DESC LIMIT 2')]
        con.execute('UPDATE posts SET views=0 WHERE id=?',(ids[0],))
        con.execute('UPDATE posts SET views=NULL WHERE id=?',(ids[1],));con.commit()
    top={x['id']:x for x in c.get('/api/nails/posts').json()['items']}
    assert top[ids[0]]['views']==0 and top[ids[1]]['views'] is None
    assert all(x['performance_index'] is None for x in top.values())


def test_schema_only_database_has_no_report(tmp_path):
    from nail_dashboard.db import init_db
    path=tmp_path/'empty.sqlite3';init_db(path)
    with TestClient(create_app(path)) as c:
        result=c.get('/api/nails/overview')
        assert result.status_code==503 and 'seed' in result.json()['detail']


def test_js_handler_brand_resets_page(setup):
    """Executes actual JS function with minimal URL state; this is NOT browser E2E."""
    if not shutil.which('node'):pytest.skip('Node.js not installed')
    js=Path(__file__).parents[1].joinpath('static/app.js')
    script='''const fs=require('fs'),vm=require('vm'),assert=require('assert');
    const src=fs.readFileSync(process.argv[1],'utf8').replace(/bootstrap\\(\\);\\s*$/,'');
    const location={href:'http://127.0.0.1/nails?page=2&brand=all#v-top',get hash(){return new URL(this.href).hash}};
    const history={pushState(_a,_b,url){location.href=String(url)}};
    const ctx=vm.createContext({location,history,URL,document:{},encodeURIComponent,console});
    vm.runInContext(src,ctx);vm.runInContext("brandList=[{slug:'mellow'}];render=()=>{};chooseBrand('mellow')",ctx);
    assert(location.href.includes('page=1'));assert(location.href.includes('brand=mellow'));
    assert.equal(vm.runInContext('percent(null)',ctx),'—');assert.equal(vm.runInContext('percent(0)',ctx),'0%');
    console.log('PASS JS brand reset + percent null semantics');'''
    result=subprocess.run(['node','-e',script,str(js)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,(result.stdout,result.stderr)
