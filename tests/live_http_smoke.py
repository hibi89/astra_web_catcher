"""External HTTP smoke test with two Uvicorn processes and dedicated persistent temp DB."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parent.parent

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def start(env,p):
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(p)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            with urlopen(f'http://127.0.0.1:{p}/api/health',timeout=.7) as res:
                if res.status==200:return proc
        except Exception:time.sleep(.1)
    proc.kill();raise RuntimeError('uvicorn did not respond')

def call(base,path,method='GET',payload=None,cookie=None):
    headers={'Content-Type':'application/json'}
    if cookie:headers['Cookie']=cookie
    data=json.dumps(payload).encode() if payload is not None else None
    try:
        with urlopen(Request(base+path,data=data,method=method,headers=headers),timeout=8) as res:
            return res.status,{k.lower():v for k,v in res.headers.items()},json.load(res) if 'json' in res.headers.get('content-type','') else res.read().decode()
    except HTTPError as e:
        return e.code,{k.lower():v for k,v in e.headers.items()},json.load(e)

def main():
    with tempfile.TemporaryDirectory(prefix='astra-real-http-') as temp:
        env=os.environ.copy();env['ASTRA_DB_PATH']=str(Path(temp)/'persist.db')
        subprocess.run([sys.executable,'-m','app.db','seed'],cwd=ROOT,env=env,check=True,capture_output=True)
        p=port();base=f'http://127.0.0.1:{p}'
        proc=start(env,p)
        try:
            status,headers,user=call(base,'/api/auth/login','POST',{'username':'demo_a','password':'DemoPass!2026'})
            assert status==200 and user['username']=='demo_a'
            cookie=headers['set-cookie'].split(';',1)[0]
            status,_,cart=call(base,'/api/shop/cart','POST',{'product_id':1,'quantity':1},cookie)
            assert status==201 and cart['quantity']==1
            status,_,book=call(base,'/api/jobs/postings/1/bookmark','POST',cookie=cookie)
            assert status==200 and book['ok']
        finally:
            proc.terminate();proc.wait(timeout=5)
        proc=start(env,p)
        try:
            assert call(base,'/api/shop/cart',cookie=cookie)[2]['items'][0]['quantity']==1
            assert len(call(base,'/api/jobs/me',cookie=cookie)[2]['bookmarks'])==1
            status,_,order=call(base,'/api/shop/orders','POST',{'request_key':'real_restart_test'},cookie)
            assert status==201 and order['total']>0
            assert call(base,'/api/shop/orders/'+str(order['id']),cookie=cookie)[0]==200
            assert call(base,'/api/shop/cart')[0]==401
            assert call(base,'/shop')[0]==200 and call(base,'/jobs')[0]==200
            print('LIVE HTTP PASS: Uvicorn start, login, cart write, bookmark write, process restart, persistence, order, auth, pages')
            print('DB exists:',Path(env['ASTRA_DB_PATH']).is_file())
        finally:
            proc.terminate();proc.wait(timeout=5)

if __name__=='__main__':main()
