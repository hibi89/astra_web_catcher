"""Runs against temporary SQLite DB; never changes the development DB."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient
from app.db import get_db, seed_db
from app.main import app


@pytest.fixture()
def env(tmp_path,monkeypatch):
    db_path=tmp_path/'test_only.db'
    monkeypatch.setenv('ASTRA_DB_PATH',str(db_path))
    assert seed_db() is True
    with TestClient(app) as c:
        yield c, db_path


def login(client, who='demo_a'):
    r=client.post('/api/auth/login',json={'username':who,'password':'DemoPass!2026'})
    assert r.status_code==200,r.text
    assert 'httponly' in r.headers['set-cookie'].lower()
    assert 'samesite=lax' in r.headers['set-cookie'].lower()
    return client


def choose(conn, sql,params=()):return conn.execute(sql,params).fetchone()[0]


def test_public_catalog_counts_search_sort_filter_paging(env):
    c,_=env
    p=c.get('/api/shop/products').json()
    assert p['total']==24 and len(p['items'])==8 and p['pages']==3
    r=c.get('/api/shop/products',params={'q':'파이썬'})
    assert r.json()['total']==1 and r.json()['items'][0]['author']=='이서윤'
    bycat=c.get('/api/shop/products',params={'category':1}).json()
    assert bycat['total']==5
    asc=c.get('/api/shop/products',params={'sort':'price_asc'}).json()['items']
    desc=c.get('/api/shop/products',params={'sort':'price_desc'}).json()['items']
    assert asc[0]['price']<=asc[-1]['price'] and desc[0]['price']>=desc[-1]['price']
    assert c.get('/api/shop/products?page=3').json()['items']
    assert c.get('/api/shop/products?page=4').json()['items']==[]
    assert c.get('/api/shop/products/999999').status_code==404
    assert c.get('/api/shop/products?sort=invalid').status_code==422


def test_seed_and_reset_idempotence(env):
    c,dbpath=env
    assert dbpath.is_file()
    assert seed_db() is False
    with get_db() as d:
        assert choose(d,'SELECT COUNT(*) FROM products')>=20
        assert choose(d,'SELECT COUNT(*) FROM categories')>=4
        assert choose(d,'SELECT COUNT(*) FROM companies')>=6
        assert choose(d,'SELECT COUNT(*) FROM job_postings')>=20
        assert choose(d,'SELECT COUNT(*) FROM products WHERE stock=0')>=1
        assert choose(d,'SELECT COUNT(*) FROM job_postings WHERE is_closed=1')>=2


def test_auth_status_codes_origin_and_validation(env):
    c,_=env
    assert c.get('/api/shop/cart').status_code==401
    assert c.get('/api/shop/orders').status_code==401
    assert c.get('/api/jobs/me').status_code==401
    assert c.post('/api/jobs/postings/1/apply',json={'note':'hello'}).status_code==401
    assert c.post('/api/auth/login',json={'username':'demo_a','password':'wrong'}).status_code==401
    login(c)
    assert c.get('/api/auth/me').json()['username']=='demo_a'
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':1,'user_id':2}).status_code==422
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':0}).status_code==422
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':-3}).status_code==422
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':1.5}).status_code==422
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':1},headers={'Origin':'https://example.com'}).status_code==403
    assert c.post('/api/auth/logout').status_code==200
    assert c.get('/api/shop/cart').status_code==401


def test_cart_quantity_and_empty_stock(env):
    c,_=env;login(c)
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':2}).status_code==201
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':1}).json()['quantity']==3
    assert c.get('/api/shop/cart').json()['items'][0]['quantity']==3
    assert c.patch('/api/shop/cart/1',json={'quantity':0}).status_code==422
    assert c.patch('/api/shop/cart/1',json={'quantity':99}).status_code==409
    assert c.patch('/api/shop/cart/1',json={'quantity':2}).status_code==200
    assert c.post('/api/shop/cart',json={'product_id':4,'quantity':1}).status_code==409
    assert c.delete('/api/shop/cart/1').status_code==200
    assert c.get('/api/shop/cart').json()['items']==[]
    assert c.delete('/api/shop/cart/1').status_code==404


def test_order_stock_price_snapshot_idempotence_and_privacy(env):
    c,_=env;login(c)
    price=c.get('/api/shop/products/1').json()['price']
    stock=c.get('/api/shop/products/1').json()['stock']
    assert c.post('/api/shop/cart',json={'product_id':1,'quantity':2}).status_code==201
    # Payload price and user ID are not trusted: extra fields rejected.
    assert c.post('/api/shop/orders',json={'request_key':'test_order_1','total':1}).status_code==422
    create=c.post('/api/shop/orders',json={'request_key':'test_order_1'})
    assert create.status_code==201
    o=create.json(); assert o['total']==2*price and not o['replayed']
    replay=c.post('/api/shop/orders',json={'request_key':'test_order_1'})
    assert replay.status_code==200 and replay.json()['id']==o['id'] and replay.json()['replayed']
    assert c.get('/api/shop/cart').json()['items']==[]
    assert c.get('/api/shop/products/1').json()['stock']==stock-2
    assert c.get('/api/shop/orders/'+str(o['id'])).json()['items'][0]['unit_price']==price
    with get_db() as d: d.execute('UPDATE products SET price=price+12000 WHERE id=1')
    assert c.get('/api/shop/orders/'+str(o['id'])).json()['total']==2*price
    assert c.get('/api/shop/orders/'+str(o['id'])).json()['items'][0]['title_snapshot']
    b=TestClient(app);login(b,'demo_b')
    assert b.get('/api/shop/orders/'+str(o['id'])).status_code==404
    assert b.get('/api/shop/orders').json()==[]
    assert b.get('/api/shop/cart').json()['items']==[]


def test_order_atomic_out_of_stock(env):
    c,_=env;login(c)
    c.post('/api/shop/cart',json={'product_id':1,'quantity':1})
    c.post('/api/shop/cart',json={'product_id':2,'quantity':1})
    with get_db() as d:
        before=choose(d,'SELECT stock FROM products WHERE id=1')
        d.execute('UPDATE products SET stock=0 WHERE id=2')
    assert c.post('/api/shop/orders',json={'request_key':'atomic_test_1'}).status_code==409
    with get_db() as d:
        assert choose(d,'SELECT stock FROM products WHERE id=1')==before
        assert choose(d,'SELECT COUNT(*) FROM orders')==0
        assert choose(d,'SELECT COUNT(*) FROM cart_items WHERE user_id=1')==2


def test_parallel_users_one_remaining_stock(env):
    a,_=env;login(a);b=TestClient(app);login(b,'demo_b')
    with get_db() as d: d.execute('UPDATE products SET stock=1 WHERE id=1')
    assert a.post('/api/shop/cart',json={'product_id':1,'quantity':1}).status_code==201
    assert b.post('/api/shop/cart',json={'product_id':1,'quantity':1}).status_code==201
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(client.post,'/api/shop/orders',json={'request_key':f'concurrent_{i}_key'}) for i,client in enumerate([a,b])]
        responses=[f.result() for f in futures]
    assert sorted(r.status_code for r in responses)==[201,409]
    with get_db() as d:
        assert choose(d,'SELECT stock FROM products WHERE id=1')==0
        assert choose(d,'SELECT COUNT(*) FROM orders')==1
        assert choose(d,'SELECT COUNT(*) FROM cart_items')==1


def test_parallel_same_idempotency_key(env):
    a,_=env;login(a);a.post('/api/shop/cart',json={'product_id':1,'quantity':1})
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(a.post,'/api/shop/orders',json={'request_key':'same_key_parallel'}) for _ in range(3)]
        rs=[f.result() for f in futures]
    assert sorted(r.status_code for r in rs)==[200,200,201]
    assert len({r.json()['id'] for r in rs})==1
    with get_db() as d:assert choose(d,'SELECT COUNT(*) FROM orders')==1


def test_jobs_multi_filters_experience_semantics(env):
    c,_=env
    all_posts=c.get('/api/jobs/postings',params={'open_only':False}).json()
    assert all_posts['total']==26 and c.get('/api/jobs/postings').json()['total']==23
    assert c.get('/api/jobs/postings',params={'role':'없는 직무'}).json()['total']==0
    assert c.get('/api/jobs/postings',params={'q':'서비스 개발','role':'백엔드','region':'서울','open_only':False}).json()['total']>0
    assert c.get('/api/jobs/postings',params={'experience':-2}).status_code==422
    for experience in (0,2,4,8):
        data=c.get('/api/jobs/postings',params={'experience':experience,'open_only':False,'page':1}).json()
        # Verify all records, including paginated results.
        for page in range(1,data['pages']+1):
            for post in c.get('/api/jobs/postings',params={'experience':experience,'open_only':False,'page':page}).json()['items']:
                assert post['career_any'] or post['min_years']<=experience and (post['max_years'] is None or post['max_years']>=experience)
    assert c.get('/api/jobs/postings/99999').status_code==404
    assert c.get('/api/jobs/postings?page=2').status_code==200


def test_bookmark_and_application_acl_duplicates(env):
    a,_=env;login(a)
    b=TestClient(app);login(b,'demo_b')
    job=1
    assert a.post(f'/api/jobs/postings/{job}/bookmark').status_code==200
    assert a.post(f'/api/jobs/postings/{job}/bookmark').status_code==200
    assert len(a.get('/api/jobs/me').json()['bookmarks'])==1
    assert len(b.get('/api/jobs/me').json()['bookmarks'])==0
    assert a.get(f'/api/jobs/postings/{job}/status').json()['bookmarked'] is True
    assert a.delete(f'/api/jobs/postings/{job}/bookmark').status_code==200
    assert a.get(f'/api/jobs/postings/{job}/status').json()['bookmarked'] is False
    assert a.post('/api/jobs/postings/999999/bookmark').status_code==404
    assert a.post(f'/api/jobs/postings/{job}/apply',json={'note':'X'}).status_code==422
    assert a.post(f'/api/jobs/postings/{job}/apply',json={'note':'  '}).status_code==422
    assert a.post(f'/api/jobs/postings/{job}/apply',json={'note':'경험을 공유하고 싶습니다.','user_id':2}).status_code==422
    r=a.post(f'/api/jobs/postings/{job}/apply',json={'note':'경험을 공유하고 싶습니다.'})
    assert r.status_code==201
    assert a.post(f'/api/jobs/postings/{job}/apply',json={'note':'다시 지원'}).status_code==409
    aid=r.json()['id']
    assert a.get('/api/jobs/applications/'+str(aid)).json()['note']=='경험을 공유하고 싶습니다.'
    assert b.get('/api/jobs/applications/'+str(aid)).status_code==404
    assert len(a.get('/api/jobs/me').json()['applications'])==1
    assert b.get('/api/jobs/me').json()['applications']==[]
    assert a.get('/api/jobs/applications/99999').status_code==404
    assert a.post('/api/jobs/postings/3/apply',json={'note':'마감된 공고'}).status_code==409


def test_parallel_duplicate_application(env):
    a,_=env;login(a)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=[pool.submit(a.post,'/api/jobs/postings/1/apply',json={'note':'동시 지원 테스트'}) for _ in range(2)]
        rs=[f.result() for f in future]
    assert sorted(r.status_code for r in rs)==[201,409]
    with get_db() as d:assert choose(d,'SELECT COUNT(*) FROM applications WHERE job_id=1 AND user_id=1')==1


def test_persistence_new_connection(env):
    a,path=env;login(a)
    assert a.post('/api/jobs/postings/1/bookmark').status_code==200
    assert a.post('/api/shop/cart',json={'product_id':1,'quantity':1}).status_code==201
    assert path.exists()
    with get_db() as d:assert choose(d,'SELECT COUNT(*) FROM bookmarks')==1
    with TestClient(app) as restarted_client:
        login(restarted_client)
        assert len(restarted_client.get('/api/jobs/me').json()['bookmarks'])==1
        assert len(restarted_client.get('/api/shop/cart').json()['items'])==1


def test_pages_assets_and_health(env):
    c,_=env
    for path in ('/','/shop','/shop/cart','/shop/products/1','/shop/orders','/shop/orders/1','/jobs','/jobs/me','/jobs/postings/1','/jobs/applications/1'):
        r=c.get(path);assert r.status_code==200 and 'ASTRA' in r.text
    for path in ('/static/app.js','/static/style.css'):
        assert c.get(path).status_code==200
    assert c.get('/static/secrets.txt').status_code==404
    assert c.get('/api/health').json()['ok']
