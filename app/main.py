"""Astra Web Catcher: two independent fictional, database-backed local MVPs."""
import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import get_db, check_password

app = FastAPI(title='Astra Web Catcher local MVP', version='0.1.0')
STATIC = Path(__file__).parent / 'static'
COOKIE = 'astra_session'
SESSION_TTL = 60 * 60 * 12


class OriginCheck(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('origin')
            # For browser cookie mutation requests, reject requests from other origins.
            if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
                return Response(content='{"detail":"Cross-origin request rejected"}',media_type='application/json',status_code=403)
        return await call_next(request)

app.add_middleware(OriginCheck)


def db():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

DB = Annotated[sqlite3.Connection, Depends(db)]


def user_id(conn: DB, session: Annotated[str | None, Cookie(alias=COOKIE)] = None) -> int:
    if not session:
        raise HTTPException(401,'Login required')
    token = hashlib.sha256(session.encode()).hexdigest()
    row=conn.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires_at>?',(token,int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401,'Session missing or expired')
    return row['user_id']

User = Annotated[int, Depends(user_id)]


def find_one(conn, sql, params=(), status=404):
    row=conn.execute(sql,params).fetchone()
    if not row:
        raise HTTPException(status,'Resource not found')
    return dict(row)


def positive_qty(n: int):
    if n<1 or n>100: raise HTTPException(422,'Quantity must be 1..100')
    return n


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Login(Strict):
    username: str = Field(min_length=1,max_length=50)
    password: str = Field(min_length=1,max_length=200)


class CartAdd(Strict):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1,le=100, strict=True)


class CartUpdate(Strict):
    quantity: int = Field(ge=1,le=100, strict=True)


class PlaceOrder(Strict):
    request_key: str = Field(min_length=8,max_length=128,pattern=r'^[a-zA-Z0-9_:-]+$')


class ApplicationCreate(Strict):
    note: str = Field(min_length=2,max_length=1000)

    @field_validator('note')
    @classmethod
    def non_blank(cls, v):
        if not v.strip(): raise ValueError('Note must not be blank')
        return v.strip()


@app.get('/api/health')
def health(conn: DB):
    conn.execute('SELECT 1').fetchone()
    return {'ok':True,'mode':'local','db':'sqlite'}


@app.post('/api/auth/login')
def login(body: Login, response: Response, conn: DB):
    row=conn.execute('SELECT id,username,password_hash FROM users WHERE username=?',(body.username,)).fetchone()
    if not row or not check_password(body.password,row['password_hash']):
        raise HTTPException(401,'Invalid credentials')
    token=secrets.token_urlsafe(32)
    conn.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],int(time.time())+SESSION_TTL))
    response.set_cookie(COOKIE,token,httponly=True,samesite='lax',secure=os.environ.get('ASTRA_SECURE_COOKIE')=='1',max_age=SESSION_TTL,path='/')
    return {'id':row['id'],'username':row['username']}


@app.post('/api/auth/logout')
def logout(response: Response, conn: DB, session: Annotated[str | None, Cookie(alias=COOKIE)] = None):
    if session:
        conn.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(session.encode()).hexdigest(),))
    response.delete_cookie(COOKIE,path='/')
    return {'ok':True}


@app.get('/api/auth/me')
def me(conn: DB, uid: User):
    return find_one(conn,'SELECT id, username FROM users WHERE id=?',(uid,))


@app.get('/api/shop/categories')
def categories(conn: DB):
    return [dict(r) for r in conn.execute('SELECT id,name FROM categories ORDER BY id')]


@app.get('/api/shop/products')
def products(conn: DB, q: str = Query('',max_length=100), category: int | None = Query(None,gt=0),
             sort: str = Query('id',pattern='^(id|price_asc|price_desc)$'), page: int = Query(1,ge=1,le=10000)):
    where=['1=1']; args=[]
    if q.strip():
        where.append('(p.title LIKE ? OR p.author LIKE ?)')
        args.extend([f'%{q.strip()}%',f'%{q.strip()}%'])
    if category is not None:
        where.append('p.category_id=?');args.append(category)
    predicate=' AND '.join(where)
    total=conn.execute(f'SELECT COUNT(*) FROM products p WHERE {predicate}',args).fetchone()[0]
    order={'id':'p.id','price_asc':'p.price ASC,p.id','price_desc':'p.price DESC,p.id'}[sort]
    rows=conn.execute(f'SELECT p.*,c.name AS category_name FROM products p JOIN categories c ON c.id=p.category_id WHERE {predicate} ORDER BY {order} LIMIT 8 OFFSET ?',args+[(page-1)*8]).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'pages':max(1,(total+7)//8)}


@app.get('/api/shop/products/{product_id}')
def product_detail(product_id: int, conn: DB):
    return find_one(conn,'SELECT p.*,c.name AS category_name FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?',(product_id,))


@app.get('/api/shop/cart')
def cart(conn: DB, uid: User):
    items=[dict(r) for r in conn.execute('''SELECT ci.product_id,ci.quantity,p.title,p.author,p.price,p.stock
           FROM cart_items ci JOIN products p ON p.id=ci.product_id WHERE ci.user_id=? ORDER BY ci.id''',(uid,))]
    return {'items':items,'total':sum(i['price']*i['quantity'] for i in items)}


@app.post('/api/shop/cart',status_code=201)
def cart_add(body: CartAdd, conn: DB, uid: User):
    try:
        conn.execute('BEGIN IMMEDIATE')
        product=find_one(conn,'SELECT stock FROM products WHERE id=?',(body.product_id,))
        current=conn.execute('SELECT quantity FROM cart_items WHERE user_id=? AND product_id=?',(uid,body.product_id)).fetchone()
        amount=(current['quantity'] if current else 0)+body.quantity
        if amount>100: raise HTTPException(422,'Cart item quantity exceeds 100')
        if amount>product['stock']: raise HTTPException(409,'Not enough stock')
        conn.execute('''INSERT INTO cart_items(user_id,product_id,quantity) VALUES (?,?,?)
            ON CONFLICT(user_id,product_id) DO UPDATE SET quantity=excluded.quantity''',(uid,body.product_id,amount))
        conn.commit()
        return {'product_id':body.product_id,'quantity':amount}
    except Exception:
        conn.rollback();raise


@app.patch('/api/shop/cart/{product_id}')
def cart_update(product_id: int, body: CartUpdate, conn: DB, uid: User):
    try:
        conn.execute('BEGIN IMMEDIATE')
        row=find_one(conn,'SELECT ci.id,p.stock FROM cart_items ci JOIN products p ON p.id=ci.product_id WHERE ci.user_id=? AND ci.product_id=?',(uid,product_id))
        if body.quantity>row['stock']: raise HTTPException(409,'Not enough stock')
        conn.execute('UPDATE cart_items SET quantity=? WHERE id=?',(body.quantity,row['id']))
        conn.commit()
        return {'product_id':product_id,'quantity':body.quantity}
    except Exception:
        conn.rollback();raise


@app.delete('/api/shop/cart/{product_id}')
def cart_remove(product_id: int, conn: DB, uid: User):
    row=conn.execute('DELETE FROM cart_items WHERE user_id=? AND product_id=? RETURNING id',(uid,product_id)).fetchone()
    if not row: raise HTTPException(404,'Cart item not found')
    return {'ok':True}


@app.post('/api/shop/orders',status_code=201)
def place_order(body: PlaceOrder, response: Response, conn: DB, uid: User):
    try:
        # SQLite BEGIN IMMEDIATE serializes competing writers across requests/connections.
        conn.execute('BEGIN IMMEDIATE')
        previous=conn.execute('SELECT id,total FROM orders WHERE user_id=? AND request_key=?',(uid,body.request_key)).fetchone()
        if previous:
            conn.commit()
            response.status_code=200
            return {'id':previous['id'],'total':previous['total'],'replayed':True}
        items=conn.execute('''SELECT ci.product_id,ci.quantity,p.title,p.price FROM cart_items ci
               JOIN products p ON p.id=ci.product_id WHERE ci.user_id=? ORDER BY ci.product_id''',(uid,)).fetchall()
        if not items: raise HTTPException(409,'Cart is empty')
        total=sum(r['quantity']*r['price'] for r in items)
        for r in items:
            changed=conn.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',(r['quantity'],r['product_id'],r['quantity']))
            if changed.rowcount!=1: raise HTTPException(409,'Not enough stock for the complete order')
        cur=conn.execute('INSERT INTO orders(user_id,request_key,total) VALUES (?,?,?)',(uid,body.request_key,total))
        oid=cur.lastrowid
        conn.executemany('INSERT INTO order_items(order_id,product_id,title_snapshot,unit_price,quantity) VALUES (?,?,?,?,?)',
                         [(oid,r['product_id'],r['title'],r['price'],r['quantity']) for r in items])
        conn.execute('DELETE FROM cart_items WHERE user_id=?',(uid,))
        conn.commit()
        return {'id':oid,'total':total,'replayed':False}
    except Exception:
        conn.rollback();raise


@app.get('/api/shop/orders')
def orders(conn: DB, uid: User):
    return [dict(r) for r in conn.execute('SELECT id,total,created_at FROM orders WHERE user_id=? ORDER BY id DESC',(uid,))]


@app.get('/api/shop/orders/{order_id}')
def order_detail(order_id: int, conn: DB, uid: User):
    obj=find_one(conn,'SELECT id,total,created_at FROM orders WHERE id=? AND user_id=?',(order_id,uid))
    obj['items']=[dict(r) for r in conn.execute('SELECT product_id,title_snapshot,unit_price,quantity FROM order_items WHERE order_id=?',(order_id,))]
    return obj


@app.get('/api/jobs/meta')
def job_meta(conn: DB):
    return {'roles':[r[0] for r in conn.execute('SELECT DISTINCT role FROM job_postings ORDER BY role')],
            'regions':[r[0] for r in conn.execute('SELECT DISTINCT region FROM job_postings ORDER BY region')]}


@app.get('/api/jobs/postings')
def jobs(conn: DB, q: str = Query('',max_length=100),role: str = Query('',max_length=50),region: str = Query('',max_length=50),
         experience: int | None = Query(None,ge=0,le=60),open_only: bool = True,page: int = Query(1,ge=1,le=10000)):
    where=['1=1']; params=[]
    if q.strip():
        where.append('(j.title LIKE ? OR j.body LIKE ? OR c.name LIKE ?)')
        params.extend([f'%{q.strip()}%']*3)
    if role:where.append('j.role=?');params.append(role)
    if region:where.append('j.region=?');params.append(region)
    if experience is not None:
        # Experience = candidate years; any-career OR range containing candidate years.
        where.append('(j.career_any=1 OR (j.min_years<=? AND (j.max_years IS NULL OR j.max_years>=?)))')
        params.extend([experience,experience])
    if open_only:where.append('j.is_closed=0')
    predicate=' AND '.join(where)
    joins='FROM job_postings j JOIN companies c ON c.id=j.company_id'
    total=conn.execute(f'SELECT COUNT(*) {joins} WHERE {predicate}',params).fetchone()[0]
    rows=conn.execute(f'''SELECT j.*,c.name AS company_name {joins} WHERE {predicate} ORDER BY j.id DESC LIMIT 8 OFFSET ?''',params+[(page-1)*8]).fetchall()
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'pages':max(1,(total+7)//8),
            'filter_definition':'experience = candidate years, inclusive min/max; career_any always matches'}


@app.get('/api/jobs/postings/{job_id}')
def job_detail(job_id: int, conn: DB):
    return find_one(conn,'SELECT j.*,c.name AS company_name,c.about AS company_about FROM job_postings j JOIN companies c ON c.id=j.company_id WHERE j.id=?',(job_id,))


@app.get('/api/jobs/me')
def job_mypage(conn: DB, uid: User):
    saved=[dict(r) for r in conn.execute('''SELECT j.id,j.title,j.role,j.region,c.name AS company_name,b.created_at
        FROM bookmarks b JOIN job_postings j ON j.id=b.job_id JOIN companies c ON c.id=j.company_id WHERE b.user_id=? ORDER BY b.id DESC''',(uid,))]
    applied=[dict(r) for r in conn.execute('''SELECT a.id AS application_id,a.job_id,a.note,a.created_at,j.title,c.name AS company_name
        FROM applications a JOIN job_postings j ON j.id=a.job_id JOIN companies c ON c.id=j.company_id WHERE a.user_id=? ORDER BY a.id DESC''',(uid,))]
    return {'bookmarks':saved,'applications':applied}


@app.get('/api/jobs/postings/{job_id}/status')
def job_status(job_id: int, conn: DB, uid: User):
    find_one(conn,'SELECT id FROM job_postings WHERE id=?',(job_id,))
    return {'bookmarked':bool(conn.execute('SELECT 1 FROM bookmarks WHERE user_id=? AND job_id=?',(uid,job_id)).fetchone()),
            'applied':bool(conn.execute('SELECT 1 FROM applications WHERE user_id=? AND job_id=?',(uid,job_id)).fetchone())}


@app.post('/api/jobs/postings/{job_id}/bookmark')
def bookmark(job_id: int, conn: DB, uid: User):
    find_one(conn,'SELECT id FROM job_postings WHERE id=?',(job_id,))
    conn.execute('INSERT OR IGNORE INTO bookmarks(user_id,job_id) VALUES (?,?)',(uid,job_id))
    return {'ok':True,'bookmarked':True}


@app.delete('/api/jobs/postings/{job_id}/bookmark')
def unbookmark(job_id: int, conn: DB, uid: User):
    conn.execute('DELETE FROM bookmarks WHERE user_id=? AND job_id=?',(uid,job_id))
    return {'ok':True,'bookmarked':False}


@app.post('/api/jobs/postings/{job_id}/apply',status_code=201)
def apply(job_id: int, body: ApplicationCreate, conn: DB, uid: User):
    try:
        conn.execute('BEGIN IMMEDIATE')
        job=find_one(conn,'SELECT is_closed FROM job_postings WHERE id=?',(job_id,))
        if job['is_closed']:raise HTTPException(409,'Posting is closed')
        if conn.execute('SELECT 1 FROM applications WHERE user_id=? AND job_id=?',(uid,job_id)).fetchone():
            raise HTTPException(409,'Already applied to this posting')
        cur=conn.execute('INSERT INTO applications(user_id,job_id,note) VALUES (?,?,?)',(uid,job_id,body.note))
        conn.commit()
        return {'id':cur.lastrowid,'job_id':job_id}
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(409,'Already applied to this posting')
    except Exception:
        conn.rollback();raise


@app.get('/api/jobs/applications/{application_id}')
def application_detail(application_id: int, conn: DB, uid: User):
    return find_one(conn,'''SELECT a.id,a.job_id,a.note,a.created_at,j.title,c.name AS company_name
            FROM applications a JOIN job_postings j ON j.id=a.job_id JOIN companies c ON c.id=j.company_id
            WHERE a.id=? AND a.user_id=?''',(application_id,uid))


@app.get('/static/{asset}')
def static(asset: str):
    if asset not in {'app.js','style.css'}:raise HTTPException(404)
    return FileResponse(STATIC/asset)


@app.get('/')
def root():
    return FileResponse(STATIC/'index.html')


@app.get('/{page:path}',include_in_schema=False)
def ui(page: str):
    if page=='shop' or page.startswith('shop/') or page=='jobs' or page.startswith('jobs/'):
        return FileResponse(STATIC/'index.html')
    raise HTTPException(404,'Unknown page')
