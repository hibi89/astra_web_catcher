# Test Report — 2026-10-18 (KST)

## 실제 실행한 명령과 결과

- `python -m app.db seed` → 초기 DB 생성 성공. `users=2`, `categories=5`, `products=24`, `companies=7`, `job_postings=26`.
- `python -m pytest -q --disable-warnings --maxfail=1` → **13 passed in 3.01s** (초기 `pytest -q`는 프로젝트 import 경로 미설정으로 실패, `pytest.ini` 추가 후 재검증).
- `python tests/live_http_smoke.py` → **LIVE HTTP PASS**: Uvicorn 서버 시작, 로그인, 카트/관심 저장, 프로세스 종료·재시작, DB 영속성, 주문 생성, 보호 API 401, 공개 HTML 응답 200. 임시 전용 DB 사용.
- `node --check app/static/app.js` → PASS(구문 검증).
- `python -m compileall -q app tests` → PASS(Python 바이트코드 컴파일).
- `TestClient(app).get('/api/health')` → 200 `{"ok":true,"mode":"local","db":"sqlite"}`.
- `python tests/browser_smoke.py` → **미통과**: Chromium이 `http://127.0.0.1:<port>/shop`에 대해 `net::ERR_BLOCKED_BY_ADMINISTRATOR` 반환. Direct proxy 플래그 방식으로 재시도해도 동일. 브라우저 E2E는 통과로 기록하지 않음. 스크린샷 생성되지 않음.

로그: `logs/pytest-first.log`, `logs/pytest-second.log`, `logs/syntax.log`, `logs/browser-first.log`, `logs/browser-second.log`, `logs/live-http.log`, `logs/pytest-final.log`. 생성 로그는 Git 저장소 제외 대상이므로 현재 작업 산출물 ZIP에는 포함할 수 있습니다.

## 테스트별 기대 / 실제 / 판정

| 테스트명 | 실행 방법 | 기대 | 실제 결과 | 판정 |
| --- | --- | --- | --- | --- |
| 시드 개수·중복 시드 | `test_seed_and_reset_idempotence` | 기준 개수 및 중복 없음 | 24권/7회사/26공고/계정2, 중복 재삽입 없음 | 통과 |
| 도서 목록·검색·분류·정렬·페이지 | `test_public_catalog_counts_search_sort_filter_paging` | 조건별 정확한 DB 결과, 404/422 | 기대한 건수/순서/상태 코드 | 통과 |
| 비로그인/쿠키/Origin/입력 | `test_auth_status_codes_origin_and_validation` | 401·422·403 및 쿠키 속성 | 전부 기대 일치 | 통과 |
| 카트 중복 합산/수정/삭제 | `test_cart_quantity_and_empty_stock` | 합산·재고 제한·삭제 | 전부 기대 일치 | 통과 |
| 주문·재고·멱등·소유권·가격 스냅샷 | `test_order_stock_price_snapshot_idempotence_and_privacy` | 재고 차감 1회, B 접근 차단, 원 가격 보존 | 기대 일치 | 통과 |
| 주문 재고 부족 롤백 | `test_order_atomic_out_of_stock` | 일부 차감·주문 생성 없음 | 원 재고/카트 그대로, 주문 0 | 통과 |
| 병렬 사용자 A/B 재고 1개 | `test_parallel_users_one_remaining_stock` | 201 한 명, 409 한 명 | 201/409, 재고 0, 주문 1 | 통과 |
| 병렬 동일 주문 키 3요청 | `test_parallel_same_idempotency_key` | 주문 ID 1개, 재고 1번 차감 | 201/200/200, 동일 ID | 통과 |
| 채용 복합 필터·경력 포함 조건 | `test_jobs_multi_filters_experience_semantics` | AND 조건 + 포함 경력 범위 | 기대한 결과 일치 | 통과 |
| 관심 등록/해제·지원 ACL·중복·마감 | `test_bookmark_and_application_acl_duplicates` | 본인 기록, 중복 409/마감 409 | 기대 일치 | 통과 |
| 병렬 동일 공고 지원 | `test_parallel_duplicate_application` | 201+409, 지원 1건 | 기대 일치 | 통과 |
| 영속성/새 DB 접속 | `test_persistence_new_connection` | 다시 연결해도 카트·관심 보존 | 기대 일치 | 통과 |
| HTML 정적 경로·헬스체크 | `test_pages_assets_and_health` | 200 정상 반환, 존재하지 않는 정적 파일 404 | 기대 일치 | 통과 |
| Uvicorn HTTP 프로세스 재시작 | `python tests/live_http_smoke.py` | 세션 및 카트·관심 영속성, 주문/HTML HTTP 정상 | 실제 서버 프로세스 2회 실행, 재시작 후 데이터 보존·주문/페이지 성공 | 통과 |
| Playwright Chromium UI | `python tests/browser_smoke.py` | 클릭/주문/지원/화면 캡처 | 탐색 전 차단됨 | **미실행(환경 차단)** |
| 생산 빌드 / 타입 검사 | `node --check`, `compileall` | 선택 스택 코드가 실행 가능 | 구문/컴파일 통과, Next.js·TypeScript 빌드 대상 아님 | **대체 검증** |

## 사용자 PC에서 남은 검증

1. `python -m app.db seed` → `python -m uvicorn app.main:app --port 8000`.
2. Chrome/Edge에서 `http://127.0.0.1:8000/shop`와 `/jobs` 열기, 검색/상세/로그인/카트/주문/지원 흐름 확인.
3. 개발자도구 Console 및 Network에서 JS 오류/4xx 확인. UI 스크린샷 수집.
4. `python tests/browser_smoke.py`를 실행하려면 시스템 Chromium 경로(`CHROME_EXECUTABLE`/PATH/Playwright 설치 브라우저)를 각 PC 실행 경로로 변경하거나 Playwright 설치 브라우저로 대체. 현재는 시스템 특화된 실행 파일 경로입니다.
5. 서비스 재시작 후 카트·주문·관심·지원 데이터 보존 확인.

## 2026-10-18 16:35 KST — 독립 재검증

사용자 보고: /shop 및 /jobs에서 주문·지원 흐름과 새로고침 후 유지 확인(사용자 수동 검증; ChatGPT 브라우저 직접 실행 결과가 아님).

**새로 실제 실행한 명령:**
- `python -m pytest -q tests/test_mvp.py` → **13 passed in 2.88s** (별도 temp SQLite DB; 동일 세션에서 앞서 13 passed in 3.14s).
- `python tests/live_http_smoke.py` → **LIVE HTTP PASS**: Uvicorn 실제 프로세스 종료·재시작 후 카트·관심 저장, 주문 생성·세션 유지. 별도 임시 SQLite DB.
- `python tests/live_integrity_check.py` → **6/6 PASS**: 실제 Uvicorn HTTP, 두 세션, 독립 임시 SQLite DB. 테스트 종료 시 임시 DB 삭제.

| 추가 실제 테스트 | 기대 결과 | 실제 결과 | 판정 |
| --- | --- | --- | --- |
| A/B 본인 데이터 격리 | A의 장바구니·지원·관심이 B에게 노출되지 않음 | 사용자별 각자 항목 확인, 타인 지원 상세 HTTP 404 | 통과 |
| 프로세스 재시작 | 세션·장바구니·관심·지원 내역 유지 | Uvicorn terminate 후 새 PID 서버 기동, 전 항목 다시 조회 성공 | 통과 |
| 주문 금액·재고 | 9,000원×2=18,000원, 재고 -2 | 18,000원 응답·재고 -2, 카트 비움 | 통과 |
| 금액 조작·가격 스냅샷 | 조작 거절, 가격 수정 후 기존 주문 불변 | 클라이언트 total=1 요청 422, DB 가격 +7,777원 수정 후 총액 18,000원 유지 | 통과 |
| 주문 키 재전송·소유권 | 재전송 신규 주문 금지, 타인 주문 접근 차단 | 재전송 200/replayed=true, 기존 주문 1건·재고 추가 차감 0, B 상세 404 | 통과 |
| 재고 1개 병렬 HTTP | 201 1건·409 1건, 재고 0 | 별개 세션 동시 POST, 201/409, order_items 1행 | 통과 |
| 동일 공고 동시 HTTP 지원 | 201 1건·409 1건, DB 1건 | 동시 POST 201/409, 후속 반복 409, DB 1행 | 통과 |
| 최종 A/B 주문·지원 조회 | 서로의 주문·지원 상세 접근 불가 | A 소유 내역에만 표시; B 상세 404 | 통과 |

**미검증:** 이 실행 환경에서는 Chromium 실제 조작/Console/Network 시연이 여전히 정책 차단됨. 사용자 수동 조작 성공 보고와 독립 테스트 통과를 혼동하지 않음. 실사용 부하·운영 보안 검증은 범위 밖.

**재현용 코드:** `tests/live_integrity_check.py` (GitHub 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`). 로컬 실행 로그 `logs/pytest-2026-10-18-recheck.log`, `logs/live-http-2026-10-18-recheck.log`, `logs/live-integrity-2026-10-18.log` (로그 파일 자체는 Git 추적 대상 아님).

## 2026-10-19 KST — p4 client-rendered owner Chart/Table

### 실제 실행

- `python -m pytest -q -ra tests/test_owner_client_chart_table.py tests/test_synthetic_owner_isolation.py tests/test_synthetic_sqlite_dashboard.py` → **53 passed, 1 warning**. 신규 client 계약 7건, 기존 owner isolation 33건, 기존 synthetic SQLite API 13건.
- `python -m compileall -q app astra_contracts scripts tests` → **PASS**.
- `node --check astra_contracts/owner_client_chart_table.js` → **PASS**.
- `python -m scripts.p4_owner_client_chart_table_browser_smoke --schema examples/p4_owner_demo_schema.json --rows examples/p4_owner_demo_rows.json` → **PASS**, Windows Chromium 156.0.8078.4, 실제 loopback HTTP + shared synthetic SQLite `:memory:`.
- Chromium 시나리오: A/B 각각 3행의 브라우저 렌더링, 교차 owner 404, 0행 상태, API 네트워크 실패 후 재시도, 변조된 행/자체 해시 응답 거부, 다른 owner 응답 거부, 지연된 이전 응답 무시, 같은 턴 중복 fetch 1회, Chart/Table 마우스·Enter·Space·화살표, 320/390/768/1366 viewport, XSS 문자열 text-only, JavaScript 예외 0, 예상 밖 Console 오류 0, 외부 요청 0. 의도된 교차 owner 404와 고의 네트워크 실패는 오류 증거에서 별도로 분류했다.

### 전체 Python 회귀

- 전체 저장소 명령 `python -m pytest -q -ra --tb=no tests`도 Python 3.12.14 Windows에서 실행했다. UTF-8 모드, 임시 Python 의존성, Selenium, 허용된 TEMP 경로, Python PATH를 설정한 최종 실행은 **752 passed, 96 failed, 108 errors, 3 skipped, 2 warnings**. 전체 회귀는 통과하지 않았다.
- 세 건 skip: pinned OWID archive가 제공되지 않은 두 증거 통합 테스트와 Windows symlink capability skip 1건. 원래 752/96/108 실행의 per-test JUnit/log는 없고 `.pytest_cache/v/cache/lastfailed`는 Windows 및 WSL에서 권한 거부되어 정확한 실패별 분포를 복구하지 못했다.
- 대표 재현(별도 로컬 환경): Python 3.11.9/pytest 9.1.1의 3-test 실행은 exit 1, 3 failed. `test_exact_repository_migration_blob`은 `core.autocrlf=true`, `git ls-files --eol`의 `i/lf w/crlf`와 실제 hash 불일치(`5f5bd...` 기대, `ab965a...` 작업 파일)로 재현됐다. `test_symlink_destination_refused`는 앱 코드 전에 `WinError 1314`로 실패했다. 생성 앱 하위 pytest의 18초 timeout은 plugin autoload 비활성화 후에도 재현됐다.
- timeout 진단: 생성 앱 pytest가 1개 테스트를 수집한 뒤 TestClient 요청에서 멈췄다. DB가 없는 빈 `FastAPI()` 앱의 `TestClient.get('/')`도 8초 timeout이라, 이 재현에서 SQLite 잠금은 확인되지 않았다. 이전에 기록한 SQLite subprocess lock은 현재 로그가 없어 미확정으로 정정한다. 752/96/108 전체를 환경 또는 제품 결함으로 일반화하지 않는다.
- 기준 커밋의 과거 **940 passed / 2 skipped**, Actions run `39225637124`는 이번 소스 결과가 아니다. `.github/workflows/p4-owner-isolation.yml`에 신규 계약 테스트와 Chromium E2E를 추가했지만 원격 workflow는 실행하지 않았다(원격 push 금지 유지).

상세 기록과 재현 안내: `docs/P4_CLIENT_RENDERED_OWNER_CHART_TABLE_20261019.md`. 기존 `/preview`, 전체 owner isolation 코드·tests는 보존했다. 실제 고객 데이터/API, 운영 인증, 의미 승인, production/deployment는 미사용·미승인이다.
