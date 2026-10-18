"""Runs Chromium UI against a dedicated ephemeral SQLite DB and collects screenshots.
Usage: python tests/browser_smoke.py
"""
import os
import shutil
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent
SCREEN=ROOT/'screenshots'
SCREEN.mkdir(exist_ok=True)

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    with tempfile.TemporaryDirectory(prefix='astra-browser-') as temp:
        env=os.environ.copy()
        env['ASTRA_DB_PATH']=str(Path(temp)/'browser_test.db')
        subprocess.run([sys.executable,'-m','app.db','seed'],cwd=ROOT,env=env,check=True,capture_output=True)
        port=free_port();base=f'http://127.0.0.1:{port}'
        proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            for _ in range(70):
                try:
                    with urllib.request.urlopen(base+'/api/health',timeout=1) as r:
                        if r.status==200:break
                except Exception:time.sleep(.15)
            else:raise RuntimeError('Server did not start')
            with sync_playwright() as p:
                browser_path=os.environ.get('CHROME_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
                launch={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
                if browser_path:launch['executable_path']=browser_path
                browser=p.chromium.launch(**launch)
                page=browser.new_page(viewport={'width':1360,'height':900},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda ex:errors.append(str(ex)))
                page.on('console',lambda m:errors.append('console: '+m.text) if m.type=='error' else None)
                page.goto(base+'/shop',wait_until='networkidle')
                page.locator('.tile').first.wait_for()
                assert page.locator('.tile').count()==8
                page.screenshot(path=str(SCREEN/'01-shop-list.png'),full_page=True)
                page.get_by_role('button',name='로그인').click()
                page.get_by_role('dialog').get_by_role('button',name='로그인').click()
                page.get_by_text('demo_a',exact=True).wait_for()
                page.locator('.tile').first.get_by_text('상세 보기').click()
                page.get_by_role('button',name='장바구니 담기').click()
                page.get_by_text('장바구니 수량').wait_for()
                page.get_by_role('link',name='장바구니',exact=True).click()
                page.locator('#order-btn').wait_for()
                page.screenshot(path=str(SCREEN/'02-shop-cart.png'),full_page=True)
                page.locator('#order-btn').click()
                page.get_by_text('주문 상세').wait_for()
                assert '테스트 주문' in page.locator('main').inner_text() or '주문 #' in page.locator('main').inner_text()
                page.screenshot(path=str(SCREEN/'03-shop-order.png'),full_page=True)
                page.goto(base+'/jobs',wait_until='networkidle')
                page.locator('.jobtile').first.wait_for()
                assert page.locator('.jobtile').count()==8
                page.locator('select[name=role]').select_option('백엔드')
                page.get_by_role('button',name='검색').click()
                page.wait_for_url('**/jobs?*')
                page.locator('.jobtile').first.wait_for()
                assert all('백엔드' in t for t in page.locator('.jobtile').all_inner_texts())
                page.screenshot(path=str(SCREEN/'04-jobs-filter.png'),full_page=True)
                page.locator('.jobtile').first.locator('a').click()
                page.get_by_role('button',name='관심 공고 저장').click()
                page.get_by_role('button',name='관심 해제').wait_for()
                page.locator('#note').fill('로컬 테스트 지원 메모입니다.')
                page.get_by_role('button',name='테스트 지원서 제출').click()
                page.get_by_text('이미 지원한 공고입니다.').wait_for()
                page.screenshot(path=str(SCREEN/'05-job-detail.png'),full_page=True)
                page.get_by_role('link',name='내 관심·지원 내역').click()
                page.get_by_text('지원 내역 (1)').wait_for()
                page.screenshot(path=str(SCREEN/'06-jobs-mypage.png'),full_page=True)
                page.reload(wait_until='networkidle')
                page.get_by_text('지원 내역 (1)').wait_for()
                assert not errors,'JS console errors: '+repr(errors)
                print('BROWSER PASS: shop list, login, cart, order, jobs filter, bookmark, apply, mypage, reload')
                print('JS errors:',errors)
                print('Screenshots:',*[str(x) for x in sorted(SCREEN.glob('*.png'))],sep='\n  ')
                browser.close()
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()

if __name__=='__main__':main()
