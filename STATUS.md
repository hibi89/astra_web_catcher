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
