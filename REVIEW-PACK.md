# AI Reviewer Pack — Independent MVPs

## 구현 범위

자체 샘플을 가진 도서 쇼핑몰 **북하버**(`GET /shop`)와 가상 구인 플랫폼 **커리어웨이**(`GET /jobs`). 동일 FastAPI 서버·SQLite 데이터베이스와 로컬 데모 인증을 공유하되 각자의 도메인 엔드포인트/화면을 분리. 24 도서, 5 분류, 7 회사, 26 공고, A/B 계정 제공.

## 핵심 데이터 흐름

1. `app/static/app.js` 목록 입력 → `GET /api/shop/products?...` → SQL 검색·정렬·pagination → 목록 출력.
2. `POST /api/shop/cart` → 세션으로 user 결정 → `(user,product)` 유일 항목을 누적 수량으로 갱신.
3. `POST /api/shop/orders` → `BEGIN IMMEDIATE` → 중복 키 확인 → DB 가격/재고 재조회 → 조건부 차감 → 주문+스냅샷 저장 → 카트 삭제 → COMMIT.
4. `GET /api/jobs/postings?...` → 직무/지역/후보 연차 포함조건 SQL AND 필터.
5. `POST /api/jobs/postings/{id}/bookmark`/`apply` → 세션 검증 및 UNIQUE 제약 → `GET /api/jobs/me`로 소유 데이터만 읽기.

## 핵심 경로

- 스키마: `migrations/001_initial.sql`
- 시드/DB 연결: `app/db.py`
- 서버/권한/트랜잭션: `app/main.py`
- UI: `app/static/index.html`, `app/static/app.js`, `app/static/style.css`
- 테스트: `tests/test_mvp.py`, `tests/browser_smoke.py`, `tests/live_http_smoke.py`
- 사용법: `README.md`
- 설계: `ARCHITECTURE.md`
- 결과/로그: `TEST-REPORT.md`, `logs/*` (로컬)

## 실행 증거

- 2026-10-18 로컬 환경에서 `python -m pytest -q` → **13/13 통과**, 총 3.01초.
- Node JS 구문 검사, Python compileall, ASGI health→200 성공. 별도 Uvicorn HTTP 서버를 2회 가동해 세션·카트·관심·주문 영속성 확인.
- **브라우저 UI 검증은 완료되지 않음**: Chromium이 로컬 서버 접속을 관리자 정책으로 차단. `tests/browser_smoke.py`, `tests/live_http_smoke.py` 스크립트 존재하지만 성공 로그·스크린샷 없음.

## 알려진 문제 / 미검증

- 요청 원안의 Next.js/TypeScript/Prisma 대신 FastAPI 사용: 외부 npm 레지스트리 DNS 장애로 설치 불가능. TS typecheck/Next.js build 해당 없음.
- 실제 Chromium에서 화면 조작/콘솔/네트워크 검증 불가; 사용자 PC에서 E2E 필요.
- 원티드 공개 사이트 직접 관찰 실패. 구현은 제공된 명세 기준 자체 설계.
- Playwright 실행 환경에서 로컬 HTTP 탐색 자체가 제한되므로 사용자 Windows/Chrome에서 추가 확인 필요.
- 실사용 인증 시스템 아님. 소유권/API 동작은 테스트, 모든 브라우저·프록시 설정의 CSRF/보안 검증은 미완료.

## 운영 전 추가 작업

정식 로그인/비밀번호 관리, TLS+Secure 쿠키, CSRF 강화, rate limit, 데이터 보호·백업, DB migration runner, DB 서버 전환, 운영 부하 테스트, 보안 스캔, 메일/실제 결제/실제 지원 프로세스(별도 승인이 필요한 신규 범위), 관측/에러 추적, 접근성/모바일 E2E, 디자이너 시연에 따른 UX 보완. 테스트 계정과 시드 데이터는 절대 운영에 사용하지 말 것.

## 추가 검증 증거 (2026-10-18 16:35 KST)

- 사용자가 실제 브라우저에서 두 앱의 주문·지원·새로고침 유지 성공을 보고했으며 이는 사용자 수동 시연(모델 직접 관찰 아님).
- 독립 실행: pytest 13/13 PASS(2.88초), 실제 Uvicorn HTTP 재시작 스모크 PASS, `tests/live_integrity_check.py` 6/6 PASS.
- 실 HTTP 결과: A/B 접근 격리(타인 상세 404), 서버 재기동 데이터 유지, 원 단위 서버 주문 18,000원·재고 -2·금액 위변조 422, 가격 스냅샷·멱등, 재고 1개 병렬 주문 201/409, 동시 중복 지원 201/409·DB 1건.
- 기존 초기 검증 시점의 '브라우저 검증 미완료'와 별개로 사용자 수동 동작 보고가 추가되었음. 모델이 실제 Chromium을 직접 제어한 검증이나 콘솔 오류 검사는 여전히 미완료.
- 근거: GitHub 추가 테스트 `tests/live_integrity_check.py` 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`; 최종 명령·출력은 `TEST-REPORT.md`.
