# Astra Web Catcher — 독립 로컬 MVP 2종

가상의 **북하버**(도서 쇼핑몰, `/shop`) 및 **커리어웨이**(채용 서비스, `/jobs`)를 한 로컬 서버에서 실행하는 실습 프로젝트입니다. YES24·원티드는 공개 서비스 흐름 참고 대상으로만 사용했습니다. 실제 업체·상품·채용 공고·주문·지원 데이터를 사용하거나 외부 서비스로 전송하지 않습니다.

## 기술 선택과 환경 제약

원안은 Next.js + TypeScript + Prisma + SQLite였으나, 검증 환경의 npm 패키지 레지스트리 DNS가 `EAI_AGAIN`으로 차단되고 빈 GitHub 저장소에 기존 소스가 없었습니다. 그래서 **이미 설치된 FastAPI 0.128 / Python 3.13 / SQLite / vanilla JavaScript**를 이용했습니다. 단일 프로세스, 별도 프론트엔드 번들 단계 없음, 각 API에 SQL DB 직접 연결이라는 장점이 있습니다. **이 결과물을 Next.js/Prisma/TypeScript 구현으로 부르면 안 됩니다.** TypeScript 검사와 Next.js production build는 이 스택에 해당하지 않습니다. Python 컴파일·JS 구문 검사·ASGI 구동으로 대체 검증했습니다.

## 설치 / 초기화 / 실행

요구사항: Python 3.11+ (검증: Python 3.13), 로컬 포트 8000, SQLite (Python 내장), npm 불필요. 프로젝트 루트에서:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.db init
python -m app.db seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`init`은 **기존 데이터 보존**하며 스키마를 생성하고, `seed`는 DB에 사용자가 이미 있을 경우 전체 샘플을 중복 생성하지 않습니다. 실행에 필요한 네트워크는 첫 `pip install`뿐입니다. 검증 환경에는 필요한 패키지가 설치되어 있었습니다.

실행 후:

- 시작: <http://127.0.0.1:8000/>
- 도서 목록: <http://127.0.0.1:8000/shop>
- 장바구니: <http://127.0.0.1:8000/shop/cart>
- 주문 내역: <http://127.0.0.1:8000/shop/orders>
- 채용 목록: <http://127.0.0.1:8000/jobs>
- 채용 마이페이지: <http://127.0.0.1:8000/jobs/me>
- API 명세(OpenAPI): <http://127.0.0.1:8000/docs>

### 테스트 계정 (로컬 데모 전용)

| 사용자 | 아이디 | 비밀번호 |
| --- | --- | --- |
| A | `demo_a` | `DemoPass!2026` |
| B | `demo_b` | `DemoPass!2026` |

기본 비밀번호는 실사용을 위한 것이 아닙니다. DB에는 PBKDF2-SHA256 salt 기반 해시만 저장합니다. 인증 쿠키는 HttpOnly/SameSite=Lax, HTTPS 구동 시 `ASTRA_SECURE_COOKIE=1`로 Secure 활성화하세요. 외부에 서비스를 노출하지 마세요.

### 테스트 · 정적 분석

```bash
python -m pytest -q
node --check app/static/app.js      # Node 설치 시에만
python -m compileall -q app tests
python tests/live_http_smoke.py  # 별도 Uvicorn 프로세스 2회로 재시작/영속성 검증
python tests/browser_smoke.py        # Playwright 설치 + 로컬 Chromium 필요
```

테스트는 `tmp_path` 하위 **별도 SQLite DB**를 생성하며 개발 DB의 데이터를 변경하지 않습니다. 브라우저 스모크 테스트도 별도 임시 DB를 사용하도록 작성했습니다. **2026-10-18 검증 환경에서는 Chromium 로컬 HTTP 탐색이 `ERR_BLOCKED_BY_ADMINISTRATOR`로 차단되어 브라우저 시연을 완료하지 못했습니다.** 테스트는 미실행/환경 차단으로 기록하고 통과 처리하지 않았습니다. 로컬 PC에서는 `playwright install chromium` 후 `python tests/browser_smoke.py`를 실행할 수 있습니다. 스모크 스크립트는 `CHROME_EXECUTABLE` 환경변수 또는 PATH의 `chromium`/`google-chrome`을 우선하며, 없으면 Playwright 설치 Chromium을 사용합니다. Windows에서는 `playwright install chromium` 후 실행할 수 있습니다.

### 데이터 및 초기화 경고

기본 DB는 `data/app.db`이고 `ASTRA_DB_PATH`로 변경할 수 있습니다. DB 파일은 `.gitignore`로 제외합니다.

**경고: 다음 명령은 선택한 DB와 사용자의 모든 장바구니·주문·관심·지원 내역을 영구 삭제합니다. 실행 전 백업하세요.**

```bash
# Linux/macOS
ASTRA_ALLOW_RESET=YES python -m app.db reset
python -m app.db seed

# Windows PowerShell
$env:ASTRA_ALLOW_RESET='YES'; python -m app.db reset
python -m app.db seed
```

개발 DB 초기화를 원하지 않으면 `reset`을 실행하지 마세요. SQLite 파일을 백업하려면 서버를 종료하고 `data/app.db`를 복사하세요. WAL 모드의 실행 중 백업은 SQLite 온라인 백업 기능을 사용하세요.

## 구현 범위 및 의도적 제외

도서: DB 조회·검색/카테고리·정렬·페이지·상세·장바구니 합산/수정/삭제·트랜잭션 주문/재고·idempotency·가격 스냅샷·본인 주문 상세. 채용: DB 조회·키워드/직무/지역/경력/진행 상태 복합 필터·상세·관심 등록/해제·메모 지원·중복 방지·마이페이지/본인 상세. 비회원은 읽기 전용 공개 목록/상세만 허용합니다.

**의도적으로 제외:** 회원가입, 실제 결제·배송, 실제 회사 계정, 파일 업로드, 이메일 발송, 비밀번호 복구, 운영 환경 배포, 관리자. UI·데이터는 자체 제작 샘플입니다. 실제 YES24/원티드의 정책이나 백엔드 구현과 같다는 의미가 아닙니다.

## 검증 및 설계 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md): DB 관계·API·접근 제어·트랜잭션
- [`TEST-REPORT.md`](TEST-REPORT.md): 실제 테스트 로그·미검증 항목
- [`REVIEW-PACK.md`](REVIEW-PACK.md): 독립 리뷰어 전달 자료
- [`HANDOFF.md`](HANDOFF.md), [`STATUS.md`](STATUS.md): 다음 채팅 인수인계
