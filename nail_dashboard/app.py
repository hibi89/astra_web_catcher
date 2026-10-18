"""Standalone, read-only nail trend demonstration: API/aggregation/frontend separated."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Literal
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from . import repository,metrics
from .db import db_path

BASE=Path(__file__).resolve().parent
Category=Literal['all','technique','color','product','season','content']


def create_app(database=None):
    app=FastAPI(title='Nail Atlas · Fictional Dataset MVP',version='0.1.0',docs_url='/nails/api-docs',openapi_url='/nails/openapi.json')
    app.state.db_path=db_path(database)
    app.mount('/nails/static',StaticFiles(directory=BASE/'static'),name='nail-static')

    def context():
        try:
            info=repository.report(app.state.db_path)
            if not info: raise HTTPException(503,'SQLite 보고서가 없습니다. python -m nail_dashboard.db seed 명령을 실행하세요.')
            brands=repository.brands(app.state.db_path)
            rows=repository.posts(app.state.db_path)
            return info,brands,rows
        except sqlite3.Error as exc:
            raise HTTPException(503,'데모 DB를 열 수 없습니다. nail_dashboard README에 따라 초기화하세요.') from exc

    def check_brand(selection,brand_rows):
        if selection!='all' and selection not in {b['slug'] for b in brand_rows}:
            raise HTTPException(422,'알 수 없는 브랜드입니다.')

    @app.get('/',include_in_schema=False)
    def root():return RedirectResponse('/nails')

    @app.get('/nails',include_in_schema=False)
    def index():return FileResponse(BASE/'static'/'index.html',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/nails/health')
    def health():
        info,_,_=context()
        return {'ok':True,'database':'SQLite','source':info['source'],'run_id':info['id']}

    @app.get('/api/nails/reports/latest')
    def latest():
        info,_,_=context()
        return {**info,'refresh_mode':'저장된 SQLite 보고서 재조회 — 외부 수집 없음'}

    @app.get('/api/nails/brands')
    def get_brands():
        _,br,_=context()
        return {'items':br}

    @app.get('/api/nails/overview')
    def get_overview(brand:str='all'):
        report,br,rows=context();check_brand(brand,br)
        return metrics.dashboard(rows,br,date.fromisoformat(report['period_end']),brand)

    @app.get('/api/nails/tags')
    def get_tags(category:Category='all',page:int=Query(1,ge=1,le=500),per_page:int=Query(14,ge=1,le=50)):
        report,_,rows=context()
        tags,links=repository.tags_and_links(app.state.db_path)
        return metrics.tag_summary(rows,tags,links,category,date.fromisoformat(report['period_end']),page,per_page)

    @app.get('/api/nails/brands/compare')
    def get_comparison():
        report,br,rows=context()
        return metrics.compare(rows,br,date.fromisoformat(report['period_end']))

    @app.get('/api/nails/posts')
    def get_posts(brand:str='all',page:int=Query(1,ge=1,le=100),per_page:int=Query(15,ge=1,le=20)):
        _,br,rows=context();check_brand(brand,br)
        result=metrics.top_posts(rows,brand,page,per_page)
        labels=repository.post_tag_labels(app.state.db_path)
        for item in result['items']:
            item['design_tags']=labels.get(item['id'],[])
        return result

    return app

app=create_app()
