"""SQLite persistence, explicit schema migration and original fictional seed records."""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / 'data' / 'app.db'


def get_db():
    p = Path(os.environ.get('ASTRA_DB_PATH', str(DEFAULT_DB)))
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=10, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA journal_mode=WAL')
    return con


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310_000).hex()
    return f'pbkdf2_sha256$310000${salt}${digest}'


def check_password(password: str, stored: str) -> bool:
    try:
        algo, count, salt, stored_digest = stored.split('$')
        if algo != 'pbkdf2_sha256':
            return False
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(count)).hex()
        return secrets.compare_digest(digest, stored_digest)
    except (ValueError, TypeError):
        return False


def init_db():
    with get_db() as con:
        con.executescript((ROOT / 'migrations/001_initial.sql').read_text(encoding='utf-8'))
        con.execute('PRAGMA user_version=1')


def seed_db():
    init_db()
    with get_db() as con:
        con.execute('BEGIN IMMEDIATE')
        if con.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            con.rollback()
            return False
        for name in ('demo_a', 'demo_b'):
            con.execute('INSERT INTO users(username,password_hash) VALUES (?,?)', (name,hash_password('DemoPass!2026')))
        categories = ['기술', '인문', '소설', '경제', '디자인']
        con.executemany('INSERT INTO categories(name) VALUES (?)', [(c,) for c in categories])
        title_parts = [
            ('파이썬으로 만드는 작은 도구','이서윤'),('질문하는 데이터','김가온'),('가상 도시의 지도','정미래'),
            ('하루의 경제학','최도현'),('여백의 색채','박은서'),('알고리즘의 정원','조현우'),
            ('사고의 모서리','권나래'),('겨울 바다 편지','문시온'),('시장의 숨은 규칙','임재민'),
            ('웹을 잇는 방법','신하린'),('관찰자의 노트','유세진'),('달빛 도서관','전유진'),
            ('작은 사업의 숫자','홍채원'),('보이는 정보의 구조','배지호'),('타입스크립트 입문','남지완'),
            ('기억의 지층','서다인'),('한밤의 플랫폼','류지수'),('금리와 생활','강세빈'),
            ('명료한 인터페이스','민하준'),('서버의 하루','오재윤'),('비판적 독서법','정예린'),
            ('마지막 열차','진라온'),('일하는 자본','표민우'),('형태와 리듬','백단아')]
        for i,(title,author) in enumerate(title_parts):
            con.execute('INSERT INTO products(category_id,title,author,description,price,stock) VALUES (?,?,?,?,?,?)',
                        ((i%5)+1,title,author,f'{title}은(는) 새로운 관점과 실용적인 사례를 담은 가상의 도서입니다.',9000+(i*1700)%23000,0 if i==3 else 1 if i==7 else 4+(i%17)))
        companies=[('오르빗랩','작은 팀을 위한 데이터 제품을 만듭니다.'),('파인웨이브','현장 중심의 소프트웨어를 연구합니다.'),('블루스텝','사용하기 쉬운 업무 도구를 만듭니다.'),('네오리프','친환경 서비스 기술을 실험합니다.'),('모자이크웍스','다양한 디지털 경험을 설계합니다.'),('코드하버','안정적인 클라우드 인프라에 집중합니다.'),('북극성스튜디오','정보 시각화를 즐기는 디자이너 팀입니다.')]
        con.executemany('INSERT INTO companies(name,about) VALUES (?,?)',companies)
        roles=['백엔드','프론트엔드','데이터','디자인','프로덕트','AI 엔지니어']
        regions=['서울','부산','대전','원격']
        for i in range(26):
            any_exp = i%6==0
            low = 0 if any_exp else (i%5)
            high = None if any_exp or i%4==0 else low+2+(i%3)
            role=roles[i%len(roles)]; region=regions[i%len(regions)]
            con.execute('INSERT INTO job_postings(company_id,title,role,region,min_years,max_years,career_any,body,is_closed) VALUES (?,?,?,?,?,?,?,?,?)',
                        ((i%7)+1,f'{role} · 서비스 개발 {i+1}기',role,region,low,high,int(any_exp),f'{role} 포지션에서 제품을 함께 개발할 구성원을 찾는 가상 공고입니다. 협업과 문제 해결 능력을 중요하게 생각합니다.',int(i in (2,9,17))))
        con.commit()
    return True


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action', choices=('init','seed','reset'))
    args=parser.parse_args()
    if args.action=='reset':
        if os.environ.get('ASTRA_ALLOW_RESET') != 'YES':
            parser.error('Data deletion refused. Set ASTRA_ALLOW_RESET=YES explicitly.')
        for suffix in ('','-wal','-shm'):
            Path(str(os.environ.get('ASTRA_DB_PATH',DEFAULT_DB))+suffix).unlink(missing_ok=True)
    if args.action=='seed': print('Seed inserted:' ,seed_db())
    else: init_db(); print('Database initialized:',os.environ.get('ASTRA_DB_PATH',DEFAULT_DB))
