"""SQLite storage and deterministic *fictional* demonstration seed. No remote collection."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import os
import random
import sqlite3

DEFAULT_PATH = Path(__file__).resolve().parent / 'data' / 'nails.db'
SCHEMA = Path(__file__).resolve().parent / 'schema.sql'
BRANDS = [
    ('lumi', 'LUMI NAIL', '직접 시술', 48800, '#7139ef', 53),
    ('nori', 'NORI GEL', '직접 시술', 34200, '#edb63d', 48),
    ('mellow', 'MELLOW TIP', '시트형', 91200, '#fb745b', 81),
    ('pola', 'POLA NAIL', '시트형', 11800, '#a99afa', 26),
]
TAG_GROUPS = {
    'technique': ['마그넷·캣아이','미러·오로라','그라데이션','프렌치','니트','파츠·스톤','원컬러','3D·입체'],
    'color': ['시어·투명','화이트·밀키','베이지·누드','핑크','블루·그린','브라운','블랙·그레이','레드·보르도'],
    'product': ['컬러젤','젤 시트·팁','베이스·탑','아트 재료','세트·키트'],
    'season': ['봄','여름','가을','겨울','홀리데이'],
    'content': ['디자인 소개','튜토리얼','신상품 공지','이벤트'],
}
PURPOSES = TAG_GROUPS['content']


def db_path(path=None):
    return Path(path or os.environ.get('NAIL_DB_PATH') or DEFAULT_PATH)

@contextmanager
def connection(path=None):
    p=db_path(path)
    con=sqlite3.connect(f'file:{p}?mode=rw', uri=True, timeout=15)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
    finally:
        con.close()


def init_db(path=None):
    p=db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as con:
        con.executescript(SCHEMA.read_text(encoding='utf-8'))
    return p


def seed(path=None, *, reset=False):
    p=db_path(path)
    if reset and p.exists():
        p.unlink()  # deliberate destructive demo reset: CLI requires explicit --reset
    init_db(p)
    with connection(p) as con:
        if con.execute('SELECT COUNT(*) FROM posts').fetchone()[0]:
            return {'status':'skipped_existing','path':str(p)}
        rnd=random.Random(1018)
        period_end=date(2026,10,17)
        start=period_end-timedelta(days=90)
        con.execute('INSERT INTO report_runs(id,label,period_start,period_end,created_at,source) VALUES(1,?,?,?,?,?)',
                    ('Demo run 01',start.isoformat(),period_end.isoformat(),'2026-10-18T08:30:00+09:00','fictional SQLite seed'))
        for slug,name,kind,followers,color,num in BRANDS:
            con.execute('INSERT INTO brands(slug,name,business_type,follower_count,color) VALUES(?,?,?,?,?)',
                        (slug,name,kind,followers,color))
        for cat,names in TAG_GROUPS.items():
            for name in names:
                con.execute('INSERT INTO tags(category,name) VALUES(?,?)',(cat,name))
        tag_ids={(row['category'],row['name']):row['id'] for row in con.execute('SELECT * FROM tags')}
        brand_ids={row['slug']:row['id'] for row in con.execute('SELECT id,slug FROM brands')}
        for ix,(slug,name,kind,_,_,num) in enumerate(BRANDS):
            for n in range(num):
                day=start+timedelta(days=rnd.randint(0,90))
                med=rnd.choices(['reel','carousel','image'], weights=[65,27,8] if kind=='시트형' else [28,48,24])[0]
                purpose=rnd.choice(PURPOSES)
                hour=rnd.randint(9,21)
                likes=max(0, int(rnd.lognormvariate(4.9+ix*.12, .87)))
                comments=rnd.randint(0, max(1,likes//16))
                if n==0: likes=1800+ix*720  # fictional standout, still stored and aggregated
                views=None if med!='reel' or rnd.random()<.2 else (likes+comments)*rnd.randint(13,49)
                analyzed=0 if rnd.random()<.17 else 1
                url=None  # no copies/links to actual customer accounts or source posts
                cur=con.execute('INSERT INTO posts(report_id,brand_id,posted_at,hour_kst,medium,purpose,treatment,likes,comments,views,analyzed,url) VALUES(1,?,?,?,?,?,?,?,?,?,?,?)',
                                (brand_ids[slug],day.isoformat(),hour,med,purpose,'sheet' if kind=='시트형' else 'direct',likes,comments,views,analyzed,url))
                pid=cur.lastrowid
                selections=[('technique',rnd.choice(TAG_GROUPS['technique'])),('color',rnd.choice(TAG_GROUPS['color'])),('product',rnd.choice(TAG_GROUPS['product'])),('season',rnd.choice(TAG_GROUPS['season'])),('content',purpose)]
                for cat,val in selections:
                    con.execute('INSERT INTO post_tags(post_id,tag_id) VALUES(?,?)',(pid,tag_ids[(cat,val)]))
        con.commit()
        return {'status':'seeded','path':str(p),'posts':con.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 'brands':4,'tags':sum(map(len,TAG_GROUPS.values()))}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['init','seed'])
    parser.add_argument('--reset',action='store_true',help='WARNING: permanently delete existing demo SQLite data before seeding')
    parser.add_argument('--db',help='Custom database path (recommended for tests)')
    args=parser.parse_args()
    if args.reset and args.command!='seed': parser.error('--reset applies to seed only')
    print(init_db(args.db) if args.command=='init' else seed(args.db,reset=args.reset))
