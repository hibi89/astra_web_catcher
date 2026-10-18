"""End-to-end HTTP + process restart smoke using an isolated temporary SQLite file."""
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import os, socket, subprocess, sys, tempfile, time
import httpx
from nail_dashboard.db import seed


def get_port():
    with closing(socket.socket()) as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]


def run_once(path, port, root):
    env={**os.environ,'NAIL_DB_PATH':str(path)}
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','nail_dashboard.app:app','--host','127.0.0.1','--port',str(port)],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(40):
            if proc.poll() is not None:raise AssertionError(f'server failed with exit code {proc.returncode}')
            try:
                if httpx.get(base+'/nails/health',timeout=1).status_code==200:break
            except (httpx.ConnectError,httpx.ReadTimeout):pass
            time.sleep(.15)
        else: raise AssertionError('server startup timeout')
        r=httpx.get(base+'/api/nails/overview?brand=mellow',timeout=4);assert r.status_code==200
        posts=httpx.get(base+'/api/nails/posts?brand=mellow&page=2',timeout=4);assert posts.status_code==200
        html=httpx.get(base+'/nails',timeout=4);assert html.status_code==200 and b'Nail Atlas' in html.content
        invalid=httpx.get(base+'/api/nails/posts?page=0',timeout=4);assert invalid.status_code==422
        return {'summary':r.json()['summary'],'posts':posts.json(),'html':html.status_code,'invalid':invalid.status_code}
    finally:
        proc.terminate()
        try:proc.wait(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
        if proc.stderr:proc.stderr.close()


def main():
    with tempfile.TemporaryDirectory(prefix='nail-test-') as tmp:
        path=Path(tmp)/'restart.db'
        seed(path)
        original=path.read_bytes()
        root=Path(__file__).resolve().parents[2]
        first=run_once(path,get_port(),root)
        second=run_once(path,get_port(),root)
        assert first==second,'SQLite results changed across complete server restart'
        assert path.read_bytes()==original,'Read-only endpoint unexpectedly mutated database'
        print('PASS HTTP startup + /nails + 200 API + validation 422 + process stop/restart + persistent SQLite + no mutation')
        print('PASS brand=mellow page2 rows',len(second['posts']['items']))

if __name__=='__main__': main()
