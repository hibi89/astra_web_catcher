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

## 브랜드 비교 화면 스크린샷 검증
- 확인 시각: 2026-10-18 17:14:41 KST. 사용자 제공 스크린샷 1장으로 실제 가시적 브랜드 비교 화면 검증.
- 중앙에 2개 수평 막대 차트: '브랜드별 반응 중앙값' (143/245/223/2), '브랜드별 4주 성과지수' (1.26/1/0.91/결측). 아래 4개 브랜드 전부 포함한 '브랜드 상세' 표 확인.
- 우측 선택 브랜드 NAILTOWN 및 지수 1.26은 유지되지만 비교 표·차트는 4개 브랜드 전체 데이터를 포함. 브랜드 상세 8열(브랜드/구분/팔로워/분석 게시물/최근 4주 게시/반응 중앙값/4주 성과지수 중앙값/조회수 확보율) 확인.
- 상단 태그 필터는 비교 화면에서 보이지 않음. 컬러 필터가 탭으로 되돌아갈 때 보존되는지 여부는 별도 미검증.
- 증거 문서: `research/jp-nail-dashboard/BRAND_COMPARE_2026-10-18.md`, 스크린샷 검증 커밋 `e8c0d5445a225a2cc7d43d9b116aa82b2f03da81`. 원본 API/정적 데이터·차트 상호작용·공식은 미확인.
- 다음 단일 행동: 사용자가 왼쪽 '상위 게시물' 한 번 클릭 후 통보 → 연결 탭 새 상태 비교. 기존 main의 두 MVP/테스트/데이터 변경 없음; 신규 구현 보류.

## 2026-10-18 — 상위 게시물 화면 실측

- 2026-10-18 17:17:57 KST: 사용자 상위 게시물 스크린샷과 연결 브라우저 `#v-top` 읽기 전용 텍스트 교차 확인.
- **NAILTOWN 선택 유지**(상단 브랜드 탭·우측 지수 1.26). 이번 화면은 선택 브랜드 NAILTOWN의 게시물만 보이며 직전 브랜드 비교는 4개 브랜드 모두 노출.
- 표 `반응 상위 게시물`은 화면에 `1–15 / 20위` 표시, 실제 15행 노출, 이전/다음 페이지 버튼. DOM 텍스트에는 비가시적 나머지 5건까지 포함된 20행 확인.
- 표 열: 게시일, 브랜드, 형식, 디자인·컬러, 반응, 조회수, 성과지수, Instagram `보기` 링크. 첫 페이지 반응 1255 → 214 내림차순. 조회수/성과지수 결측은 `—`로 표시; 0으로 대체하면 안 됨.
- 관찰 파일 `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md` 커밋 `ff4dfaccf7999a05b5304df06b52f4cb06b6a86e`, GitHub 재조회 검증 완료.
- 미검증: 다음 페이지 동작, 외부 링크 새 탭 여부, 브랜드 전환 시 목록 재계산/페이지 초기화, API 대 정적 데이터, 원본 정렬 구현.
- **다음 단일 조작:** 표 우상단 다음(›) 버튼 1회 클릭 후 완료 보고. 신규 구현 보류, 기존 두 MVP 및 테스트 보존.

## 2026-10-18 — 상위 게시물 다중 조작 결과: 원인 미확인
- 마지막 관찰 시각 2026-10-18 17:23:40 KST. 사용자가 여러 버튼을 클릭했다고 명시했으므로 클릭 중간 인과관계는 확인 불가.
- 다시 읽은 브라우저: 상위 게시물 `#v-top` 유지, KPI 전체(153 분석/194 수집/526 반응/101 릴스), 우측 패널 4브랜드 요약, 1–15 / 20위. OHORA 반응 16,592 첫 행과 4브랜드 혼합 게시물 DOM.
- **정정:** 이 관찰만으로 '다음 클릭 시 전체 브랜드로 초기화됨'이라고 단정하지 않는다. 페이지 이동 로직/다음 5개 결과는 미검증.
- 증거: `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md` 최신 정정 커밋 `5e2343f879aad9cda6b1a750d775cd3f09462dea`. DOM이 숨긴 영역도 포함 가능함을 유지.
- 다음 단일 조작: 현재 전체 브랜드 1페이지에서 표 `다음(›)` 버튼만 한 번 누르고 즉시 메시지. 사용자 추가 스크린샷은 현재 불필요.
- 기존 main의 `/shop`, `/jobs` 및 테스트는 그대로 보존; 새 앱 구현은 계속 보류.

## 2026-10-18 — 상위 게시물 2페이지 검증 확정

- 2026-10-18 17:26:29 KST 사용자 스크린샷과 연결된 브라우저 페이지 텍스트 동시 확인. 상위 게시물 전체 브랜드 선택에서 다음(›) 클릭 후 실제 `16–20 / 20위`, 5행 노출, URL `#v-top`, 우측 4브랜드 패널 유지.
- 순위 16~20 반응 1013 (OHORA), 1012 (GELME1), 963 (OHORA), 900 (GELME1), 875 (GELME1); 각 조회수/성과지수/날짜는 관찰 문서에 기록.
- 첫 페이지의 15건 다음에 5건을 내림차순으로 표기하는 **페이지네이션은 검증 완료**. DOM은 숨긴 20건 전체 텍스트를 포함하므로 실제 노출 판정은 스크린샷 우선.
- 조사 문서 `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md` 커밋 `2c9ec93d0beacf1f01ef390d5300d64c04f077b2` 재조회 검증. 이전 다중 조작으로 인한 인과 불확실성은 새 단일 동작 관찰로 페이지네이션에 한해 해소.
- 남은 분기: 상위 게시물 화면의 페이지 2에서 브랜드 필터 변경 시 페이지 초기화/표 목록 변화, 데이터 로딩 방식·API 여부·산식 미확인.
- **다음 한 조작:** 사용자가 상단 OHORA 버튼 한 번만 클릭 후 통보. 신규 대시보드 앱 구현 보류, 기존 두 MVP와 테스트 수정 없음.

## 2026-10-18 — OHORA 브랜드 변경 및 1차 관찰 마감
- 확인 시점: 2026-10-18 17:32:53 KST. 전체 상위 게시물 2페이지(16–20/20위)에서 사용자 OHORA 단일 클릭 후 연결 브라우저 텍스트 실측. OHORA 목록 1–15/20위로 초기화; 도표 KPI 153/194/526/101 → OHORA 79/94/629/78, 우측 OHORA 상세(4주 0.91)로 변경; URL #v-top 유지.
- 결과 문서: research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md (근거 커밋 02f51a26b16098e3a4bb85931fc596f0890fbcea), 통합 재구현 명세 research/jp-nail-dashboard/OBSERVATION_CLOSEOUT_AND_MVP_SPEC_2026-10-18.md (근거 커밋 a7366eb4485ad893cce5e88b4ef4cb2e950753f4). 재조회 검증 완료.
- 네 메뉴 기본 화면, 브랜드 선택에 따른 KPI, 컬러 8태그, 4브랜드 비교, Top 20의 15+5 페이지네이션과 브랜드 변경시 페이지 1 초기화까지 관찰 완료.
- 미확인: 원본 API/정적 데이터/n8n 실제 연동, 수요지수·성과지수 정확한 공식, 보고서 조회 버튼의 외부 실행 여부, 차트/링크 부가 동작.
- 기술 선택 두 안 문서화: 독립 Next.js+TypeScript+Prisma+SQLite(권고) 대 기존 FastAPI 기반 별도 모듈. 사용자 사전 승인까지 새 코드 구현 보류.
- 원본 main /shop, /jobs, 테스트/SQLite 및 배포 설정 변경 없음. 기존 테스트 13/13과 HTTP 6/6은 과거 결과로 남김; 이 조사 단계 재실행/자동 UI 테스트 미실행.

## Nail Atlas B안: 로컬 구현·검증 완료 / GitHub 코드 미반영
- KST 확인 시각: 2026-10-18 17:56:19. 사용자가 승인한 B안으로 기존 두 MVP와 별도인 `nail_dashboard/`에서 FastAPI/SQLite/Vanilla JS 앱 실제 구현.
- 4개 가상 브랜드·208개 가상 게시물·30개 태그를 독립 SQLite에 저장. 4메뉴 대시보드/태그 분석/브랜드 비교/상위 게시물, 브랜드 필터 및 15+5 페이지네이션과 브랜드 변경시 첫 페이지 초기화(코드 계약) 구현.
- DB 접근 repository.py와 metrics.py 순수 집계, app.py FastAPI, static UI 분리. 원본 수식 미확인 항목은 데모 공식/게시물별 성과지수 null 표기. 저장 보고서 GET만 제공; 외부 수집·사용자 DB/API 미연동.
- 새 독립 temp DB pytest **15/15 PASS**, JS 구문 PASS, Python compile PASS, 별도 Uvicorn HTTP 200·422 및 서버 완전 재시작 후 데이터 유지·DB 불변 PASS. 배포 미적용.
- Browser 자동 E2E **미검증**: Playwright Chromium 내부 실행파일 없음; OS Chromium localhost/가상 인터셉트 둘 다 ERR_BLOCKED_BY_ADMINISTRATOR. 같은 방식 재시도 금지. 실제 사용자 PC용 browser_e2e.py 포함.
- 최종 로컬 산출 패키지 `Astra_P4_Nail_Atlas_B_MVP_2026-10-18.zip` 62,821바이트, SHA256 `2bae267fbd8fd49b48db4597e898b699c4651c2d22ba13e7bc8b5650f92a1c11`. 기존 앱의 테스트 결과와 섞지 않음.
- **중요:** GitHub에 직접 신규 소스 파일 18개 업로드는 현재 컨테이너 DNS 실패 및 connector 파일 바이트 전송 부재로 **미반영**. ZIP 다운로드/체크인 또는 지원 가능한 GitHub 업로드 경로 필요. 본 문서 작성과 실제 코드 체크인을 혼동 금지.
- 연구 브랜치에 `research/jp-nail-dashboard/IMPLEMENTATION_AND_QA_2026-10-18.md` 검사 보고서 커밋 `97436a163fb4357ee1eaf862a1c2fb3bd425e093`. main `dd87ffc847c7b435c7eed7b4543b7db7d184e08c` 및 기존 /shop, /jobs 보존.
- **다음 확정 작업:** 신규 소스 GitHub 체크인 → 재조회하여 18파일의 정확한 내용 검증 → 현재 PC 브라우저에서 주요 버튼 클릭·API Network·콘솔 점검 → 발견되는 오류만 수정. 추가 기능·실제 사용자 DB 연동은 미진행.

## Nail dashboard GitHub source check-in — 2026-10-18 18:03 KST

- 18 source files in nail_dashboard/ committed on research branch: 93c15d0977bdff14788667de6a527f6d89426bd3.
- Verified remote branch head and 18/18 file contents against the local source manifest.
- Earlier statement "source not committed" is now superseded. Original main /shop and /jobs are unchanged.
- Previous pytest 15/15 and live HTTP restart tests are historical results; not rerun after GitHub commit. Real Windows browser UI remains unverified.
- Next: clone research branch into new Downloads folder, pip install, seed, uvicorn 8010; test UI.

## 2026-10-18 18:18 KST — DB/API/JS regression verified 33/33

- Scope: the isolated nail_dashboard FastAPI+SQLite MVP, not original /shop or /jobs.
- Actual local command python -m pytest -q nail_dashboard/tests/test_dashboard.py => 33 passed in 1.33s, 0 failures. Previous 15 baseline plus 18 parametrized SQL/edge/JS contract cases.
- SQL rows independently checked versus brand/all KPIs, 13-week counts, hourly response median, content format average, direct/sheet type totals, brand comparison, tag SQL joins, Top20 15+5 pagination, and live DB modification.
- Empty post table, undefined denominator 0, all-zero reactions, zero posts in prior 8-week window, NULL views vs numeric 0, and absent report all verified. One discovered defect corrected: 0/0 percentage falsely displayed 0%; now API null and UI dash, with 33/33 retest PASS.
- JS state test executes chooseBrand and validates page=2 to page=1 URL reset with Node VM. This is NOT a browser click E2E; user's earlier manual browser filter verification is separate.
- Actual second command python -m nail_dashboard.tests.live_http_smoke => PASS: HTTP 200, invalid 422, two full Uvicorn starts/stops, unchanged API responses and DB bytes; Python compile and JS syntax check PASS.
- New code commit 4bc522c1f9110ad44f83d1e4b47ae0b5ce5ff87b; new regression-test commit 08ffe2f70f3d9bc2fd1e79edebe1aa3e0cd48e18. TEST-REPORT.md README.md ARCHITECTURE.md REVIEW-PACK.md updated. Work only on research/jp-nail-dashboard-20261018. main remains dd87ffc847c7b435c7eed7b4543b7db7d184e08c.
- No tests were performed against user Windows, actual Chrome E2E, n8n, customer API/DB, or production. All remain unverified/not applicable. No external app deployment.
- Next confirmed unit: user Windows browser E2E at localhost:8010/nails if requested, then review console/network if errors. Do not edit existing shop/jobs or assume original formula.

## Windows 실사용자 로컬 검증 보고 — 2026-10-18

- 사용자 Windows PowerShell 실제 실행 결과 접수: `python -m pytest -q nail_dashboard/tests/test_dashboard.py` => **33 passed in 4.57s**.
- `python -m nail_dashboard.tests.live_http_smoke` => **PASS** 실제 HTTP startup, /nails, 200/422, 프로세스 stop/restart, SQLite 영속성 및 DB 불변, `brand=mellow` 2페이지 5행.
- 위 근거는 사용자 제공 콘솔 텍스트(로컬 Windows 실행)로 확인한 결과. ChatGPT가 사용자 PC에서 별도 명령을 직접 실행하지는 않음.
- 기존 샌드박스의 33/33·HTTP 검증과 독립된 Windows 재현 성공. 브라우저 CSS/Canvas/Console/Network 자동 점검은 아직 미검증.
- 기존 main 도서 쇼핑몰/채용 MVP와 데이터 및 테스트 수정 없음. 추가 코드 수정 불필요; 다음 단계는 Windows 브라우저 UI/Console/Network 점검.

## 2026-10-18 — Windows Playwright 색상 필터 대기 실패 대응

- 사용자 Windows 실제 브라우저 테스트 첫 실행: Chromium 설치 성공; `browser_e2e.py` 태그 컬러 클릭 직후 즉시 `count()==8` assertion 실패. 화면 결과가 잘못된 것인지 아직 확인되지 않음.
- 기존 Playwright 테스트는 API 비동기 재렌더를 기다리지 않았으므로 타이밍 경합 가능. 테스트만 수정해 `expect(...).to_have_count(8)` 및 다른 뷰/페이지 전환도 최대 15초 대기·조건 진단 출력. GitHub 코드 SHA `8f50fb9b01460d9f2e98b526978237c19f5ebffc` 재조회 검증.
- 변경 소스의 Python 구문 검사 PASS, 별도 컨테이너에서 기존 pytest **33/33 PASS** 및 실제 Uvicorn 재시작 HTTP 스모크 PASS. 이 결과는 Windows Playwright 전체 성공을 의미하지 않음.
- 다음: 사용자 연구 브랜치 Git pull, 실행 중인 로컬 서버 유지, `python -m nail_dashboard.tests.browser_e2e` 재실행. 실패 시 새 진단 출력/Traceback 확인. 실제 FastAPI·SQLite·두 기존 MVP 소스는 변경 없음.

## Windows Playwright E2E 재실행 PASS — 2026-10-18 (사용자 제공 로그)

- Windows 연구 브랜치 fast-forward pull `ccdd567..457cb93` 이후 사용자 직접 실행 `python -m nail_dashboard.tests.browser_e2e` 전체 **PASS** (출력 원문 제공).
- 7개 단계 PASS: dashboard KPI 카드 3, tags 14행, color 8행, brand 비교 4행, Top posts 1페이지 15행, 2페이지 5행, mellow 브랜드 변경 후 1페이지 15행; E2E 최종 문구 및 JS pageerror/네일 API HTTP 400+ 실패 없음.
- Windows 이전 `pytest` 33/33 (4.57s), 실제 Uvicorn HTTP 재시작·SQLite 영속/무변형 PASS 결과와 결합해 **로컬 B안 MVP 핵심 자동 검증 완료**.
- 첫 Windows E2E 즉시 카운트 AssertionError 후 테스트에 비동기 UI 대기 추가한 변경본이 실제 Windows에서 통과함. 차트 렌더 DOM 값의 API 수치 대조, 모든 console.error/외부 Network, 프로덕션 보안/운영, 실제 고객 DB/API/n8n 연동은 별도 범위.
- 기존 main 쇼핑몰/채용 MVP, 기존 DB와 해당 소스·테스트 변경 없음. 이번 갱신은 검증 문서만 업데이트.

## 2026-10-18 — verified snapshot and customer-data mapping preparation

- User requested preserve already verified B MVP, **no code or original data changes**, and move to customer data connection planning based on anonymized column headers plus 5–10 sample rows.
- Created snapshot branch `snapshot/nail-atlas-b-e2e-verified-2026-10-18` at commit `343790e34967f0b20862d4ec7f5de8f084414234`; GitHub re-fetched branch commit and matched. Compared user's tested code commit `457cb9369699a74ee9706dfe922a2bcd58632919` to snapshot: only three docs changed (HANDOFF.md, STATUS.md, nail_dashboard/TEST-REPORT.md). Python/JS/SQL source unchanged.
- Read existing `nail_dashboard/{schema.sql,db.py,repository.py,metrics.py,app.py,README.md}`; published **preliminary**, not user-confirmed field mapping and formula inventory in `research/jp-nail-dashboard/DATA_INTEGRATION_MAPPING_PREP_2026-10-18.md` (commit `451a9eef1f9b241b592b46cedbb458dc903b9279`).
- Pending user input: sanitized original column names plus 5–10 representative rows from one posts dataset (IDs pseudonymized but consistently joinable; retain types/timezone and distinguish NULL vs 0). No passwords, signed URLs, individual identities, full dataset or customer DB credentials. Mapping will then classify matched/missing/derived fields and calculation feasibility; do not guess original scoring.
- Snapshot branch not used for ongoing work; no current `main` changes, no `nail_dashboard/` runtime source modifications, no production connection, no source DB modifications/import.

## 2026-10-18 — account master CSV read-only audit (294 rows)

- User supplied only `account_list(2).csv` as the **account master**, with columns account_key, username, country, image_url. File scanned read-only; 294 account records, four columns; duplicate keys/usernames/full rows 0, blanks 0.
- Country distribution: US 101 (34.35%), KR 100 (34.01%), JP 93 (31.63%). All key country prefixes match and sequential numeric suffixes within each country have zero internal gaps. No assertion about coverage of all real accounts.
- Original file remains byte-identical, sha256 `fb539da915034df23fd6faccd598cc4caf7feaba631f9f8351c1afa2b88c2e8c`; usernames, profile URLs, raw CSV not committed. Analysis report `research/jp-nail-dashboard/ACCOUNT_MASTER_AUDIT_2026-10-18.md` commit `42827af124c52fe3a44415af663387c79a63912c` was read back and verified.
- **Do not reinterpret account rows as posts or brands**; no reactions, analyzed posts, views, demand, trend or brand performance metrics computable from account list alone. A separate post dataset has not been provided in this user message; whether one exists is unconfirmed.
- Protected `snapshot/nail-atlas-b-e2e-verified-2026-10-18` remains at SHA `343790e34967f0b20862d4ec7f5de8f084414234`; no `nail_dashboard/` code, seed/customer database, existing main or raw data changes. No build/test rerun (analysis only).
- Next single question: does a separate **posts CSV** exist? If yes, provide only its anonymized field list and 5–10 example rows. Do not restructure dashboard until availability/schema confirmed.

## 2026-10-18 — two OHORA ZIPs compared read-only

- User provided `OHORA_20261016_RAW_286.zip` and `OHORA_Analysis_Ready_20261016_084112.zip`. Read-only zipfile/csv/sha256 audit: first ZIP has account master 294 + three separate snapshot exports (latest5 176 accounts/880 posts/2612 media, latest1 15/15/50, latest10 95/950/3291); second ZIP has merged analysis-ready posts 1845 unique, media 5953 unique, coverage 294 accounts (286 collected, 8 Meta error 110).
- Read-only exact cross-check: raw vs prepared post IDs 1845/1845, preserved numeric/meta values and identifiers 1845/1845; merged media all 5953 rows/all 12 fields match raw. Only 13 caption strings have one leading apostrophe added to raw text beginning '-'; reversible spreadsheet escaping behavior, intent unconfirmed. Derived followers and media counts matched all rows, engagement_count likes+comments valid in 1224 rows.
- Latest5 per account dataset has 1370 posts (271 accounts 5 posts and 15 accounts 1 post), all selected as the latest captured post by timestamp; these are *captured* posts, not full historical guarantees. Country posts KR485 US450 JP910, unequal samples/periods.
- **Likes missing 621/1845 (33.66%)**, available reactions/engagement 1224/1845; null not zero. Raw posts do not provide view counts or AI design classification, and 50-post historical backfill incomplete. No evidence of actual model provenance beyond README '홍주님 분석용 통합본'; transformation is ETL/normalization, not completed GPT trend analysis.
- Evidence doc `research/jp-nail-dashboard/RAW_VS_ANALYSIS_READY_COMPARISON_2026-10-18.md` created commit `2c17a4398192e7df586c0bd63e11dc00f5db8c09` and GitHub read back verified. No raw files or usernames/post captions/media links uploaded. Prior `account_list(2).csv` SHA exactly matches RAW ZIP account_list.csv.
- Customer DB/API not connected, no source-data modification. Existing B MVP requires `posts.likes NOT NULL`, while real rows have null likes, and there is no account-to-brand mapping; define read-only staging and nullable metrics contract before implementation. Preserve frozen `snapshot/nail-atlas-b-e2e-verified-2026-10-18` and original main.

## 2026-10-18 — user rehearsal OHORA data isolated staging test

- User clarified Oct 16 OHORA data is *practice*; proper collection expected tomorrow. User asks test current data, check original Astra acceptance, evaluate classmate dashboard construction/quality.
- **Read-only test actually executed:** unzip CSV via `zipfile/csv`; ephemeral `sqlite3.connect(':memory:')` staging with 294 accounts, 1845 posts, 5953 media; foreign key check 0, duplicate post/media IDs 0, latest5 orphan 0; both ZIP SHA256 unchanged and CRC verified. 1224 posts with observed likes+comments; 621 missing likes retained as NULL. Source user/seed DB and existing app unchanged. No claim of current Astra UI running with customer data.
- **Sampling depth bias:** KR 97 collected accounts × 5 posts (485), JP 91 × 10 (910), US 15 ×1 +79 ×5 +4 ×10 (450). Likes missing rates KR 39.79%, US 21.56%, JP 36.37%; cross-country totals/average responses cannot rank real demand.
- Results and mapping cautions committed to `research/jp-nail-dashboard/OHORA_PRACTICE_STAGING_DRY_RUN_2026-10-18.md` via GitHub. Source `REQUIREMENTS.md` confirms initial Astra accepted goal was 2 independent /shop, /jobs MVPs (previously tested); nail dashboard is later added independent mock-data MVP; generic arbitrary-URL Web Catcher and real data connection not completed.
- Do not modify `nail_dashboard` implementation or `snapshot/nail-atlas-b-e2e-verified-2026-10-18`; no customer/seed DB updates, no raw data committed. Next real integration requires equal sampling strategy, null-aware staging, account/brand separation, explicit metric contract and new full collection. Classmate implementation origin and subjective scoring not a confirmed technical result.
