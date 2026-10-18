# STATUS — Astra Web Catcher

**Updated 2026-10-18 16:17 KST**. Repository target `hibi89/astra_web_catcher` / `main` was empty at task start. Tested source developed locally under `/mnt/data/astra_web_catcher` and **22 files committed to GitHub**. Verified source commit: `62eaab17b6ee11b4a27cd7caec2fce752b8815ab`. A later documentation-only commit may advance HEAD.

## Completed locally

- One FastAPI server, two original frontends: `/shop` (BookHarbor), `/jobs` (CareerWay).
- 2 demo users; salted password hashes, 12h HttpOnly SameSite=Lax sessions; sessions determine user identity.
- 13 passing pytest tests on independently seeded temporary SQLite DBs.
- Real Uvicorn HTTP test including stop/restart and persistent cart/bookmark, test order + private API authentication PASS.
- 24 fictional books, 5 categories, 7 companies, 26 fake jobs; SQLite initial migration and idempotent seed.
- Stock-safe transactional orders with snapshots, unique request keys, parallel conflict tests; job filter, bookmark, apply, duplicate/closed guards.
- README, architecture, test report, reviewer pack, AGENTS/REQUIREMENTS, browser smoke script.
- `node --check app/static/app.js` PASS; `python -m compileall -q app tests` PASS.

## Pending / blocked

- Browser E2E and screenshots: attempted Chromium; `net::ERR_BLOCKED_BY_ADMINISTRATOR` navigating localhost. The script is available for use on another host. UI operation unverified.
- Next.js/Prisma/TypeScript original preferred tech: replaced after npm registry DNS `EAI_AGAIN` and use of available Python packages. TypeScript typecheck and Next.js production build not applicable.
- GitHub source commit `62eaab17b6ee11b4a27cd7caec2fce752b8815ab` verified with `app/main.py` and `README.md` re-fetch (22 files). No Vercel deployment requested; deployment not applicable.
- Public Wanted reference page couldn't be read; its behavior was independently designed from spec. YES24 public nav/search/cart/order links were read, no transactional operations attempted.

## Next steps

1. Re-fetch GitHub `main` HEAD and compare source and handoff document versions; initial source commit is already verified.
2. On user's localhost, install requirements, seed, start, open `/shop` and `/jobs`, inspect browser Console/Network; run `python tests/browser_smoke.py` and collect screenshots.
3. If discrepancies in reference behavior matter, request narrowly scoped user recording of search/filter/cart/order and bookmark/apply flows; no secrets/traces.
4. Update reports and resolve any actual front-end failures, then re-test; do not claim success without browser evidence.

## 2026-10-18 16:35 KST — 검증 완료 업데이트

- 사용자 직접 검증 보고: 두 앱의 주문·지원 및 새로고침 후 데이터 유지 성공. ChatGPT 브라우저 직접 검증은 기존 정책 차단으로 계속 미검증.
- 새로 실행: `python -m pytest -q tests/test_mvp.py` **13/13 PASS**, `python tests/live_http_smoke.py` **PASS**, `python tests/live_integrity_check.py` **6/6 PASS** (실제 HTTP 서버·동시 요청·독립 temp SQLite DB).
- 결과: 서버 재시작 후 A/B 세션·카트·관심·지원 영속성; 소유권 404; 서버 총액 18,000원·재고 -2·주문 스냅샷; 재고 1개 동시 주문 201/409; 중복 지원 동시 201/409·DB 1행; 주문 키 재전송 중복 방지.
- 앱 소스 변경 없음. 재현용 `tests/live_integrity_check.py` 추가, 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`. TEST-REPORT 및 REVIEW-PACK 갱신.
- **다음:** 실제 사용자 PC의 브라우저 Console/Network 검사나 문제 발견 때만 수정. 원래 요청 기술 스택과 다른 FastAPI 구현 유지 여부는 사용자 검수 결정에 따름.

## Dashboard observation research (2026-10-18 16:44 KST; isolated branch)

- Branch: research/jp-nail-dashboard-20261018, based on main dd87ffc847c7b435c7eed7b4543b7db7d184e08c.
- Document: research/jp-nail-dashboard/OBSERVATION_SPEC_2026-10-18.md.
- Connected browser tab DOM text: success. Web fetch: DisabledError. Sandbox HTTPS: DNS NameResolutionError. Neither proves source-site permission problems.
- Only initial page display observed, NOT filter/menu clicks, Network, DB, or n8n API integration.
- Formula and data source remain unverified; proposed models/endpoints are not original backend knowledge.
- Await 2–4 minute user recording/screenshots. Original main, two MVP apps, test code, and prior test outcomes preserved. Prior 13-pass suite was NOT rerun in this research phase.

## Follow-up brand filter observation: ALL / OHORA / NAILTOWN
- Recorded (KST): 2026-10-18 16:57:50. Evidence: two user-provided screenshots and read-only connected tab text, not automated click traces.
- `research/jp-nail-dashboard/BRAND_FILTER_OBSERVATIONS_2026-10-18.md` committed on isolated research branch as `dc11aa32099c746adb296fad03b58e85c6e1a7b3`.
- ALL: 153 analyzed / 194 collected, avg response 526, Reels 101 (52%), direct 71 / sheet 82.
- OHORA: 79 analyzed / 94 collected, avg response 629, Reels 78 (83%), direct 0 / sheet 79.
- NAILTOWN (connected tab): 49 analyzed / 61 collected, avg response 217, Reels 9 (15%), direct 49 / sheet 0.
- Brand selection correlates with updates to KPI, weekly chart, content response ranking, posting-hour distribution, post-type donut and right-side brand panel. Screenshots demonstrate differing states, not underlying filter algorithm.
- Still unknown: exact formulae, source API vs static JSON, click event trace, tag analysis/brand comparison/top posts interactive details.
- Next: user announces each tab/filter click; read browser again, compare with baseline, append observation, then produce gap list before any dashboard implementation.
- Existing `/shop` and `/jobs` and previous integrity test results preserved. No new tests run in this documentation update.

## 2026-10-18 17:00 KST — 태그 분석 진입 실측 및 릴스 분모 후보
- 연결된 사용자 브라우저에서 `#v-tags` 태그 분석 진입을 확인; 사용자 스크린샷과 DOM 텍스트 일치. 오른쪽 NAILTOWN 상세(지수 1.26) 표시가 유지됨.
- 상단 태그 분류 `전체` 선택; 페이지 표기 `1–14 / 37개`, 5개 분류 버튼, 열(태그/분류/게시물/수요지수/4주÷8주/판정) 확인.
- NAILTOWN 분석 49건이나 태그 테이블의 `릴스 · 디자인 소개` 66건. 우측 브랜드 선택이 태그 표를 49건 기준으로 필터링하지 않는 현상 관찰. 내부 상태/API 분리 방식 미확인.
- 릴스 비중 분모 후보: 전체 101/194=52%, OHORA 78/94=83%, NAILTOWN 9/61=15% (정수 반올림). 원본 계산 코드·다른 경우 미검증.
- 증거 파일: `research/jp-nail-dashboard/TAG_ANALYSIS_INITIAL_STATE_2026-10-18.md` 커밋 `f4f8b147a2ad1b344605d1229df9702a601bff95`.
- **다음 요청 1개:** 사용자 `태그 분석`의 `컬러` 버튼 클릭 후 완료 통지 → 동일 탭 새 스냅샷 비교. 새 앱 미구현; main 두 MVP와 테스트 보존.

## 2026-10-18 — 태그 컬러 필터 전후 관찰

- 확인 시점: 2026-10-18 17:07:08 KST. 사용자가 '컬러' 버튼 한 번 클릭한 뒤 연결 브라우저 탭의 텍스트를 재조회.
- 태그 분류 전체 37개(1–14 표시) → 컬러 8개 전체로 필터링. 테이블은 시어·투명, 화이트·밀키, 베이지·누드, 핑크, 블루·그린, 브라운, 블랙·그레이, 레드·보르도; 수요지수 1.86→0.57 내림차순.
- URL `#v-tags`와 오른쪽 NAILTOWN(1.26), 분석 49건·평균 217·릴스 9건 KPI 유지. 카테고리와 오른쪽 브랜드 패널 독립적.
- Source: `research/jp-nail-dashboard/TAG_CATEGORY_COLOR_CLICK_2026-10-18.md`; verified observation commit `451193e3b31259d7f19376f94c8f5b06624e1958`.
- 미검증: Network/API/정적 JSON, 계산식/임계치/실제 n8n 연동. 원본에서 코드·브라우저 내부 이벤트를 보지 못함.
- 다음 단일 조작은 왼쪽 `브랜드 비교` 클릭 후 재조회. 신규 앱 작업 없음; 기존 MVP, main, 이전 테스트 결과 보존.

## 브랜드 비교 전환 관찰 — 2026-10-18

- 관찰시각(KST): 2026-10-18 17:10:33; 사용자 '브랜드 비교' 클릭 후 연결 탭 URL `#v-tags` → `#v-brand`; 타이틀 브랜드 비교 확인.
- 우측 NAILTOWN 브랜드 상태(지수 1.26), 분석 49, 수집 61, 평균 반응 217, 릴스 9, 실행 #3728 유지.
- DOM에서 4개 브랜드 비교 데이터(NAILTOWN 49/143/1.26, GELME1 22/245/1.00, OHORA 79/223/0.91, EDGEU 3/2/결측)와 컬러 태그 8행 재확인.
- DOM은 숨은 화면을 포함하므로 실제 비교 화면의 그래프/표 가시성 및 컬러 필터 표시·지속 여부 **미검증**. 원본 API/정적 소스 역시 미확인.
- 원본 근거 문서 `research/jp-nail-dashboard/BRAND_COMPARE_2026-10-18.md` (커밋 `347d9a19d4711cf495524194ead8c3d91737e98d`).
- **다음 단일 입력:** 현재 브랜드 비교 화면 스크린샷 1장. 앱 구현·테스트 재실행 없으며 기존 main/DB 유지.
