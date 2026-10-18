"""Standalone read-only practice dashboard. Port 8011; does not use original MVP DB."""
from __future__ import annotations
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Literal
from .import_data import DB_DEFAULT
from . import metrics

BASE=Path(__file__).resolve().parent
Country=Literal['all','KR','US','JP']
ViewCountry=Country


def create_app(database=None):
    path=Path(database) if database else DB_DEFAULT
    app=FastAPI(title='Nail Atlas: Real CSV Practice (not market demand)',version='0.1',docs_url='/practice/api-docs')
    app.mount('/practice/static', StaticFiles(directory=BASE/'static'),name='practice-static')

    def load():
        if not path.is_file():raise HTTPException(503,f'연습용 DB 없음: python -m nail_practice.import_data --zip <분석ZIP경로>')
        try:
            with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro',uri=True) as c:
                c.row_factory=sqlite3.Row
                accounts=[dict(r) for r in c.execute('SELECT * FROM accounts ORDER BY account_key')]
                posts=[dict(r) for r in c.execute('SELECT * FROM posts ORDER BY post_id')]
                media=[dict(r) for r in c.execute('SELECT p.country,m.media_type FROM media m JOIN posts p ON p.post_id=m.post_id')]
                return accounts,posts,media
        except sqlite3.Error as e:
            raise HTTPException(503,'연습용 DB 읽기 실패') from e

    @app.get('/practice',include_in_schema=False)
    def home():return FileResponse(BASE/'static'/'index.html',headers={'Cache-Control':'no-store'})

    @app.get('/api/practice/report')
    def report():
        accounts,posts,media=load()
        dates=[p['post_date'] for p in posts]
        return {'name':'OHORA 2026-10-16 연습용 수집본','source':'분석 준비본 CSV → 별도 SQLite (수집/AI 추론 안 함)',
                'accounts':len(accounts),'posts':len(posts),'media':len(media),
                'period_start':min(dates) if dates else None,'period_end':max(dates) if dates else None}

    @app.get('/api/practice/overview')
    def overview(country:Country='all'):
        accounts,posts,media=load()
        result=metrics.overview(posts,accounts,len(media),country)
        result['stats']['media']=sum(m['country']==country for m in media) if country!='all' else len(media)
        return result

    @app.get('/api/practice/countries')
    def compare():
        accounts,posts,media=load()
        return {'items':metrics.countries(posts,accounts,media),
                'note':'계정당 수집 1/5/10건이 섞여 있으므로 국가 평균·반응 차이는 시장 규모나 인기 비교로 해석 금지.'}

    @app.get('/api/practice/accounts')
    def account_list(country:Country='all',status:Literal['all','collected','failed']='all',page:int=Query(1,ge=1,le=200),per_page:int=Query(20,ge=1,le=50)):
        accounts,posts,_=load()
        tally={}
        for p in posts:tally[p['account_key']]=tally.get(p['account_key'],0)+1
        result=[{'account_key':a['account_key'],'country':a['country'],'status':a['collection_status'],
                'posts':tally.get(a['account_key'],0),'followers_at_collection':a['followers_at_collection'],
                'error_code':a['error_code']} for a in accounts
                if (country=='all' or a['country']==country) and (status=='all' or a['collection_status']==status)]
        return {'items':result[(page-1)*per_page:page*per_page], 'total':len(result),'page':page,
                'per_page':per_page,'pages':max(1,(len(result)+per_page-1)//per_page)}

    @app.get('/api/practice/posts')
    def rank(country:Country='all',page:int=Query(1,ge=1,le=30),per_page:int=Query(15,ge=1,le=20)):
        _,posts,_=load()
        return metrics.top_posts(posts,country,page,per_page)

    @app.get('/api/practice/quality')
    def quality():
        accounts,posts,media=load()
        available=sum(p['reactions'] is not None for p in posts)
        return {'accounts':len(accounts),'collected':sum(a['collection_status']=='collected' for a in accounts),
                'failed':sum(a['collection_status']=='failed' for a in accounts),
                'posts':len(posts),'media':len(media),'reaction_available':available,
                'reaction_missing':len(posts)-available,
                'views':'미수집','design_tags':'미분류','demand_index':'미구현','purchase_intent':'미구현',
                'note':'원본 CSV는 읽기 전용. 결과는 연습용 데이터의 기술통계이며 소비자 수요/매출 추정이 아닙니다.'}
    return app

app=create_app()
