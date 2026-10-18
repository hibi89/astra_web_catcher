"""Storage adapter: all UI data comes from SQLite, never from JS arrays."""
from __future__ import annotations
from .db import connection


def report(path):
    with connection(path) as con:
        row=con.execute('SELECT * FROM report_runs ORDER BY id DESC LIMIT 1').fetchone()
        return dict(row) if row else None


def brands(path):
    with connection(path) as con:
        return [dict(row) for row in con.execute('SELECT * FROM brands ORDER BY id')]


def posts(path, *, analyzed_only=False, brand=None):
    sql='''SELECT p.*, b.slug AS brand, b.name AS brand_name, b.color AS brand_color,
        b.business_type, b.follower_count, (p.likes + p.comments) AS reactions
        FROM posts p JOIN brands b ON b.id=p.brand_id WHERE p.report_id=(SELECT MAX(id) FROM report_runs)'''
    params=[]
    if analyzed_only: sql+=' AND p.analyzed=1'
    if brand and brand!='all':
        sql+=' AND b.slug=?';params.append(brand)
    sql+=' ORDER BY p.id'
    with connection(path) as con:
        return [dict(row) for row in con.execute(sql,params)]


def tags_and_links(path):
    with connection(path) as con:
        tags=[dict(r) for r in con.execute('SELECT * FROM tags ORDER BY id')]
        relations=[dict(r) for r in con.execute('SELECT post_id,tag_id FROM post_tags')]
    return tags,relations


def post_tag_labels(path):
    with connection(path) as con:
        rows=con.execute('''SELECT pt.post_id,t.name,t.category FROM post_tags pt JOIN tags t ON t.id=pt.tag_id ORDER BY t.id''')
        result={}
        for r in rows:
            if r['category'] in ('technique','color'):
                result.setdefault(r['post_id'],[]).append(r['name'])
        return result
