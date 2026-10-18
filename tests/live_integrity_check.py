"""Real HTTP invariants test, isolated SQLite DB and disposable Uvicorn processes.

Run: python tests/live_integrity_check.py
Does not touch data/app.db or any user database.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def boot(env, port):
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError('Uvicorn stopped during startup')
        try:
            if httpx.get(f'http://127.0.0.1:{port}/api/health', timeout=0.5).status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    process.kill()
    raise RuntimeError('Uvicorn did not respond')


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def require(response, expected):
    assert response.status_code == expected, f'{response.request.method} {response.request.url.path}: expected {expected}, got {response.status_code}: {response.text[:300]}'
    return response.json()


def login(client, who):
    info = require(client.post('/api/auth/login', json={'username': who, 'password': 'DemoPass!2026'}), 200)
    assert info['username'] == who


def db_count(conn, table, where='1=1', args=()):
    return conn.execute(f'SELECT COUNT(*) FROM {table} WHERE {where}', args).fetchone()[0]


def run():
    passed = []
    with tempfile.TemporaryDirectory(prefix='astra-http-integrity-') as temp:
        db_path = Path(temp) / 'check.db'
        env = os.environ.copy()
        env['ASTRA_DB_PATH'] = str(db_path)
        subprocess.run([sys.executable, '-m', 'app.db', 'seed'], cwd=ROOT, env=env, check=True, capture_output=True)
        port = free_port()
        base = f'http://127.0.0.1:{port}'
        server = boot(env, port)
        a, b = httpx.Client(base_url=base, timeout=10), httpx.Client(base_url=base, timeout=10)
        try:
            login(a, 'demo_a')
            login(b, 'demo_b')
            assert require(a.get('/api/auth/me'), 200)['username'] == 'demo_a'
            assert require(b.get('/api/auth/me'), 200)['username'] == 'demo_b'
            require(a.post('/api/shop/cart', json={'product_id': 1, 'quantity': 2}), 201)
            require(b.post('/api/shop/cart', json={'product_id': 2, 'quantity': 1}), 201)
            require(a.post('/api/jobs/postings/1/bookmark'), 200)
            require(b.post('/api/jobs/postings/2/bookmark'), 200)
            application = require(a.post('/api/jobs/postings/1/apply', json={'note': '재시작 검증용 테스트 지원'}), 201)
            assert [i['product_id'] for i in require(a.get('/api/shop/cart'), 200)['items']] == [1]
            assert [i['product_id'] for i in require(b.get('/api/shop/cart'), 200)['items']] == [2]
            assert len(require(a.get('/api/jobs/me'), 200)['applications']) == 1
            assert require(b.get('/api/jobs/applications/' + str(application['id'])), 404)['detail'] == 'Resource not found'
            passed.append('A/B 카트·관심·지원 격리 + 타인 지원 상세 404')

            stop(server)
            server = boot(env, port)
            assert [i['product_id'] for i in require(a.get('/api/shop/cart'), 200)['items']] == [1]
            assert [i['product_id'] for i in require(b.get('/api/shop/cart'), 200)['items']] == [2]
            assert len(require(a.get('/api/jobs/me'), 200)['bookmarks']) == 1
            assert len(require(b.get('/api/jobs/me'), 200)['bookmarks']) == 1
            assert len(require(a.get('/api/jobs/me'), 200)['applications']) == 1
            passed.append('서버 프로세스 종료·재기동 후 세션/장바구니/관심/지원 유지')

            product = require(a.get('/api/shop/products/1'), 200)
            price, initial_stock = product['price'], product['stock']
            assert price > 0 and initial_stock >= 2
            require(a.post('/api/shop/orders', json={'request_key': 'integrity_order_a', 'total': 1}), 422)
            placed = require(a.post('/api/shop/orders', json={'request_key': 'integrity_order_a'}), 201)
            assert placed['total'] == 2 * price and placed['replayed'] is False
            assert require(a.get('/api/shop/products/1'), 200)['stock'] == initial_stock - 2
            assert require(a.get('/api/shop/cart'), 200)['items'] == []
            order = require(a.get('/api/shop/orders/' + str(placed['id'])), 200)
            assert order['total'] == 2 * price
            assert order['items'][0]['unit_price'] == price
            assert require(b.get('/api/shop/orders/' + str(placed['id'])), 404)['detail'] == 'Resource not found'
            replay = require(a.post('/api/shop/orders', json={'request_key': 'integrity_order_a'}), 200)
            assert replay['id'] == placed['id'] and replay['replayed'] is True
            assert require(a.get('/api/shop/products/1'), 200)['stock'] == initial_stock - 2
            with sqlite3.connect(db_path) as conn:
                conn.execute('UPDATE products SET price = price + 7777 WHERE id = 1')
                assert db_count(conn, 'orders', 'user_id=1') == 1
                assert db_count(conn, 'order_items', 'order_id=?', (placed['id'],)) == 1
            assert require(a.get('/api/shop/orders/' + str(placed['id'])), 200)['total'] == 2 * price
            passed.append(f'서버 금액 {2 * price:,}원·재고 -2·가격 보존·주문키 재전송 1건·타인 주문 404')

            require(a.post('/api/shop/cart', json={'product_id': 8, 'quantity': 1}), 201)
            require(b.post('/api/shop/cart', json={'product_id': 8, 'quantity': 1}), 201)
            assert require(a.get('/api/shop/products/8'), 200)['stock'] == 1
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(client.post, '/api/shop/orders', json={'request_key': f'race_stock_{idx}'})
                        for idx, client in enumerate((a, b))]
                results = [future.result() for future in jobs]
            assert sorted(r.status_code for r in results) == [201, 409], [(r.status_code, r.text) for r in results]
            assert require(a.get('/api/shop/products/8'), 200)['stock'] == 0
            with sqlite3.connect(db_path) as conn:
                assert db_count(conn, 'order_items', 'product_id=8') == 1
            passed.append('재고 1개에 A/B 병렬 HTTP 주문 → 201 한 건·409 한 건·재고 0')

            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(b.post, '/api/jobs/postings/2/apply', json={'note': '병렬 중복 지원 테스트'}) for _ in range(2)]
                results = [future.result() for future in jobs]
            assert sorted(r.status_code for r in results) == [201, 409], [(r.status_code, r.text) for r in results]
            assert require(b.post('/api/jobs/postings/2/apply', json={'note': '반복 지원 테스트'}), 409)['detail']
            with sqlite3.connect(db_path) as conn:
                assert db_count(conn, 'applications', 'user_id=2 AND job_id=2') == 1
            passed.append('동일 공고 병렬 HTTP 지원 → 201 한 건·409 한 건·DB 1건')

            only_a = require(a.get('/api/shop/orders'), 200)
            only_b = require(b.get('/api/shop/orders'), 200)
            assert placed['id'] in [o['id'] for o in only_a]
            assert placed['id'] not in [o['id'] for o in only_b]
            assert require(a.get('/api/jobs/applications/' + str(application['id'])), 200)['note'] == '재시작 검증용 테스트 지원'
            assert require(b.get('/api/jobs/applications/' + str(application['id'])), 404)['detail']
            passed.append('주문 목록·지원 상세 최종 A/B 권한 확인')
        finally:
            stop(server)
            a.close()
            b.close()
        assert db_path.exists()
    for idx, label in enumerate(passed, 1):
        print(f'PASS {idx}/6: {label}')
    print('RESULT: 6/6 PASS; temporary test database deleted on exit')


if __name__ == '__main__':
    run()
