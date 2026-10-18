# HANDOFF — Astra Web Catcher (ten-point operational handoff)

1. **Goal / confirmed constraints / stack:** two independently branded local functional demos from publicly visible YES24/Wanted flow patterns, no source extraction. BookHarbor `/shop`, CareerWay `/jobs`. Backend FastAPI Python 3.13, SQLite WAL; frontend vanilla HTML/CSS/JS. Next.js/Prisma original default unavailable due offline npm registry.
2. **Completed functions and decisions:** 2 users, salted PBKDF2/password verification, sessions HttpOnly/Lax, SQLite migration+seed, 24 books/5 categories/7 companies/26 jobs, cart/order/stock/idempotency, job filtering/bookmarks/applications, error states, URL filters. SQLite BEGIN IMMEDIATE chosen for atomicity and minimal setup. Fake assets only.
3. **Test commands & outcomes:** `python -m pytest -q` → **13 PASS/0 fail**. `python tests/live_http_smoke.py` → **PASS** Uvicorn real process twice + DB persistence. `node --check app/static/app.js` PASS, `python -m compileall -q app tests` PASS. Browser script `python tests/browser_smoke.py` blocked; **E2E unverified**.
4. **Status and stop point:** local code+docs usable for Python environment; **22 source/docs files committed to GitHub and core files re-read**. Browser verification remains **blocked**; no production deployment requested. Do not mark browser-tested.
5. **Failures / causes / attempted / no-repeat / alternatives:** initial `pytest -q` import error resolved with `pytest.ini`, final pass. Browser Chromium `ERR_BLOCKED_BY_ADMINISTRATOR` at localhost both default launch and direct/no-proxy; do not repeat unchanged. Network route fulfillment also blocked. Better: user-local Chrome/Playwright. npm registry DNS `EAI_AGAIN`, so Python existing dependencies reused instead of installing JS packages.
6. **Repository, branch, SHA, paths:** `hibi89/astra_web_catcher`, `main`; source commit SHA `62eaab17b6ee11b4a27cd7caec2fce752b8815ab` (22 files; verified read-back). Local `/mnt/data/astra_web_catcher`: `app/main.py`, `app/db.py`, `app/static/*`, `migrations/001_initial.sql`, `tests/test_mvp.py`, `tests/live_http_smoke.py`, `tests/browser_smoke.py`, reports.
7. **Production URL / Vercel / commands / environment:** not applicable. Run locally `python -m app.db seed`, `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Need Python 3.11+ FastAPI/Pydantic/Uvicorn installed, SQLite built-in. Local URLs `http://127.0.0.1:8000/shop`, `/jobs`.
8. **Source, backup, auth, protected data:** Source = local generated files until pushed; SQLite `data/app.db` is in `.gitignore`, don't publish. Test fixtures create isolated DB. Login seeded accounts `demo_a`/`demo_b`, `DemoPass!2026` DEMO ONLY. No real user data, external secrets, or tokens. Before reset back up DB; `ASTRA_ALLOW_RESET=YES` is explicit deletion guard.
9. **Next work & acceptance & approvals:** recheck latest GitHub HEAD, then run browser E2E on accessible localhost and correct UI issues if observed. For requested production/external hosting or exposing demo users, obtain user approval. Completion means both browser user flows, access checks, builds applicable to stack, docs and SHA verified.
10. **Timestamp / evidence / document revision SHA:** 2026-10-18 16:17 KST. Evidence: local 13 pytest passes, Uvicorn live HTTP smoke, code and syntax checks; source baseline commit `62eaab17b6ee11b4a27cd7caec2fce752b8815ab`. The current documentation-update commit will be newer than that baseline. No browser pass asserted.

## 검증 인수인계 추가 — 2026-10-18 16:35 KST

1. **목표·요구·기술:** 북하버(/shop) + 커리어웨이(/jobs) 기존 FastAPI/SQLite MVP 유지; 원래 Next.js/TS/Prisma 요구와 다름.
2. **완료·결정:** 사용자 수동으로 주문·지원·새로고침 후 유지 확인 보고. 별도 실제 HTTP 무결성 검사 스크립트 추가, 앱 기능 코드 변경 없음.
3. **명령·성공 수·미검증:** `python -m pytest -q tests/test_mvp.py` → 13/13 PASS (2.88s); `python tests/live_http_smoke.py` → PASS; `python tests/live_integrity_check.py` → 6/6 PASS. 서버 재시작, 두 사용자 ACL, 18,000원 주문·재고-2, 동시 재고 경쟁 201/409, 동시 지원 201/409·DB 1행. 실제 Chromium 자동 UI E2E는 환경 차단으로 미검증.
4. **진행·대기·중단:** 검증 요청의 API/DB 범위 완료. 브라우저 네트워크·콘솔 및 운영 수준은 미검증. 사용자 판단에 따라 기존 MVP 유지 또는 요구 스택 재구현 선택.
5. **오류·대안:** 기존 Chromium localhost ERR_BLOCKED_BY_ADMINISTRATOR 재시도 금지. 사용자의 실제 Chrome/Edge 검사로 전환, 이상 발견 시 증거에 근거한 최소 수정.
6. **저장소·브랜치·SHA·경로:** `hibi89/astra_web_catcher` / main; 검증 스크립트 추가 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`; `tests/live_integrity_check.py`, `tests/test_mvp.py`, `tests/live_http_smoke.py`, `app/main.py`, `app/db.py`, `migrations/001_initial.sql`. 이 문서 갱신 커밋은 별도로 뒤따름.
7. **배포·URL·실행 환경:** Production/Vercel 미적용. `python -m app.db seed`, `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; `http://127.0.0.1:8000/shop`, `/jobs`; Python 3.13 FastAPI SQLite.
8. **원본·백업·인증:** 테스트별 자체 temp DB 사용·종료 후 삭제, `data/app.db` 기존 개발 DB는 변경하지 않음. 데모 세션/암호 및 실제 개인정보·비밀은 GitHub 미업로드. 초기화 전 백업 필수.
9. **다음 순서·완료 기준·승인:** 현 브라우저에 오류가 있으면 Console/Network의 비밀 제외 증거 확보→최소 수정→API 회귀검증→사용자 브라우저 확인. 기술 스택 재구현은 사용자 결정 전 하지 않음.
10. **갱신 시간·확인 범위·기준 커밋:** 2026-10-18 16:35:59 KST; 테스트 로그 + 임시 DB와 실제 Uvicorn HTTP, 원격 GitHub 테스트 파일 재조회로 확인. 근거 검증 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`; 문서 갱신 SHA는 후속 커밋.

## Isolated dashboard reconnaissance addendum — 2026-10-18 16:44 KST

- Goal: observe Japan nail dashboard and prepare independent reproduction spec only, NOT implement.
- Branch: research/jp-nail-dashboard-20261018; baseline main dd87ffc847c7b435c7eed7b4543b7db7d184e08c.
- Evidence: read-only connected browser tab of daily-dashboard-ldh-1013.clevertide128.chatgpt.site displayed a KPI dashboard, 4 brands, 37 tag rows, brand comparison table, Top 20 posts, report #3728 and an n8n live-data label.
- Accessibility failures: general web DisabledError; separate Linux DNS NameResolutionError; do not assert website permissions issue.
- Unknown: action effects, metric calculations, live API versus static JSON, original schema/auth. All inferred models and endpoints in report are PROPOSALS only.
- Document: research/jp-nail-dashboard/OBSERVATION_SPEC_2026-10-18.md. Next evidence: user-operated brand toggles, tag filters, brand comparison, top posts, refresh; optional sanitized Fetch/XHR field names and statuses with no secrets.
- Preserve original /shop and /jobs, datasets, historical tests. Prior 13-pass report is historical, not a new test execution.

## Follow-up brand filter observation: ALL / OHORA / NAILTOWN
1. **Goal, scope, stack:** isolated observation (no implementation) of Japan nail dashboard; prior FastAPI/SQLite local MVPs unchanged. Recorded 2026-10-18 16:57:50 KST.
2. **Observed and rationale:** ALL/OHORA user screenshots and NAILTOWN live-tab snapshot show coherent brand-specific KPI and chart states. Use explicit evidence, avoid inferred event handlers or API assertions.
3. **Validation method/outcomes:** read-only browser tab and user screenshots; no automated browser action, network or pytest run in this step. Confirmed visual values ALL 153/526/101 Reels, OHORA 79/629/78 Reels, NAILTOWN 49/217/9 Reels.
4. **Current status:** baseline and brand-filter visual differences recorded; awaiting user-driven clicks of OHORA, tag analysis, brand compare, top posts, refresh. No development started.
5. **Failures and unknowns:** no new errors. Direct HTTP DNS failure remains previous environment constraint. Unknown client/server filtering, live n8n API, formulas, chart tooltips, report-refresh side effects. Do not repeat blocked HTTP attempts without changed conditions.
6. **Repo/branch/evidence:** `hibi89/astra_web_catcher`, `research/jp-nail-dashboard-20261018`; evidence `research/jp-nail-dashboard/BRAND_FILTER_OBSERVATIONS_2026-10-18.md` (`dc11aa32099c746adb296fad03b58e85c6e1a7b3`); initial baseline `dd87ffc847c7b435c7eed7b4543b7db7d184e08c`.
7. **Production and commands:** none for this observation; original `/shop` and `/jobs` local run instructions in main README unchanged.
8. **Protected data/backups:** original main and DB left intact; do not request cookies, tokens, passwords, HAR. Screenshot/tab excerpts are only observational evidence.
9. **Next unit and acceptance:** user clicks OHORA, says done; retrieve tab DOM and compare selected-brand KPI, charts and panel to screenshot. Continue one menu at a time. Close unknowns before first MVP implementation.
10. **Recorded (KST)/verification:** 2026-10-18 16:57:50; document commit and read-back must be verified; prior tests historical, no new E2E assertions.

## 2026-10-18 17:00 KST — 태그 분석 진입 실측 및 릴스 분모 후보
1. **Goal/scope:** Existing `/shop` and `/jobs` unchanged; dashboard reconnaissance only, isolated branch `research/jp-nail-dashboard-20261018`.
2. **Confirmed display/decision:** `#v-tags` visible and top tag filter `전체`, `1–14/37` tag rows, NAILTOWN brand panel retained (1.26). Tag row `릴스 · 디자인 소개`=66 vs NAILTOWN analyzed posts 49 suggests tag table is not scoped to currently selected brand. Do not claim confirmed API implementation.
3. **Validation:** user screenshot + read-only connected browser DOM compared. Reels denominator candidate: 101/194→52%, 78/94→83%, 9/61→15%. This is a validated arithmetic fit but **unconfirmed original calculation rule**. No pytest, browser click, network or production test performed in this step.
4. **Progress/stop:** tag-analysis first page and brand carry-over observed. Interactive category selection, pagination, brand compare and top posts pending. Stop point before clicking `컬러`.
5. **Unknown/failure/alternatives:** original JS/API/DB/n8n links and all weighting/rounding exceptions unknown; use user-operated UI snapshot rather than blocked direct scraping. No repeat of failed DNS approach.
6. **Repo/paths:** `hibi89/astra_web_catcher`, research branch, `research/jp-nail-dashboard/TAG_ANALYSIS_INITIAL_STATE_2026-10-18.md` (verified commit `f4f8b147a2ad1b344605d1229df9702a601bff95`), prior main baseline `dd87ffc847c7b435c7eed7b4543b7db7d184e08c`.
7. **Production/execution:** none in this research; existing local app execution unaffected.
8. **Original/backups/secrets:** keep main source and test DB intact; no cookies, tokens, HAR or passwords collected.
9. **Next step/acceptance:** tell user to click `컬러` exactly once and say clicked; fetch tab context and compare selected category, row count, table entries, URL and right brand panel. Then proceed one interaction at a time.
10. **Timestamp/evidence:** 2026-10-18 ~17:00 KST, screenshot `image(20261018-075954).png` and live user-connected page text. GitHub SHA/readback verified on this update; no claim of code tests.

## 2026-10-18 — 태그 컬러 필터 전후 관찰

1. **목표/범위/기술:** 2026-10-18 17:07:08 KST 읽기 전용 원본 태그 분석 확인, 별도 조사 브랜치; 기존 FastAPI/SQLite 두 MVP 변경 없음.
2. **확정 동작:** 태그 '전체' 37개 중 '컬러' 선택 후 해당 8개 컬러 행만 표시, 수요지수 내림차순 유지. NAILTOWN 우측 패널·KPI 및 `#v-tags` 유지. 서로 다른 제어 상태가 독립 동작.
3. **검증:** 사용자가 직접 '컬러' 클릭 후 동일 연결 탭 DOM 재조회; 브라우저 직접 클릭/Network 추적과 pytest는 이번 단계 미실행. 태그별 8행 값은 별도 관찰 파일에 기록.
4. **상태/중단 지점:** 태그 필터 동작 관찰 완료; 다음 메뉴 `브랜드 비교` 조작을 기다리는 중. 새 MVP 구현 전.
5. **확인 안 된 사항/실패/대안:** 실제 API/정적 자료 여부, 수요지수/판정 임계치/n8n 연동 미확인; 사용자 조작 후 브라우저 재조회로 검증. DNS/브라우저 차단 방법 무의미한 반복 금지.
6. **저장소/브랜치/경로:** `hibi89/astra_web_catcher`, `research/jp-nail-dashboard-20261018`; `research/jp-nail-dashboard/TAG_CATEGORY_COLOR_CLICK_2026-10-18.md` commit `451193e3b31259d7f19376f94c8f5b06624e1958`. main baseline `dd87ffc847c7b435c7eed7b4543b7db7d184e08c`.
7. **배포/실행:** 조사 전용 단계이므로 Production/Vercel 미적용; 기존 앱 README 실행법 유지.
8. **원본/인증/백업:** 기존 DB와 소스 보존; 인증 쿠키·토큰·개인정보 미수집.
9. **다음 작업:** 사용자에게 왼쪽 `브랜드 비교`를 한 번만 누르고 완료를 알리도록 요청. 새 DOM 스냅샷에서 URL, 브랜드 선택/패널, 비교 테이블·차트를 확인해 전후 차이를 기록.
10. **검증 시점/범위:** 2026-10-18 17:07:08 KST, UI 텍스트 스냅샷 및 연구 파일 GitHub read-back. 앱 코드/테스트 실행 없음.

## 브랜드 비교 전환 관찰 — 2026-10-18

1. 목표·범위: 젤네일 대시보드 브라우저 읽기 전용 조사. 기존 도서/채용 MVP 보존, 신규 구현 보류.
2. 확인된 변화: 사용자 클릭으로 `#v-brand` 전환, 브랜드 비교 메뉴 텍스트; NAILTOWN KPI(49/217/9)와 우측 지수 1.26 유지. 화면 텍스트에 브랜드 4곳 비교 수치 존재.
3. 검증 방법: 연결 Chrome 탭의 클릭 후 DOM 텍스트; 스크린샷/직접 클릭/Network 검사 없음. 이전 자동 테스트 결과는 유지하되 이번 단계 재실행 안 함.
4. 중단 상태: 브랜드 비교 첫 진입, 가시적 차트/표 확인 이전.
5. 미확인: DOM의 숨겨진 섹션 때문에 표/그래프의 실제 가시성, 컬러 필터 지속, API/정적 데이터, 차트 이벤트, 계산식 모두 보류. 사용자 현재 화면 스크린샷이 최단 대안.
6. 저장소·경로: `hibi89/astra_web_catcher` / `research/jp-nail-dashboard-20261018`, `research/jp-nail-dashboard/BRAND_COMPARE_2026-10-18.md`, 기록 커밋 `347d9a19d4711cf495524194ead8c3d91737e98d`; main `dd87ffc847c7b435c7eed7b4543b7db7d184e08c` 보존.
7. 배포·명령: 본 관찰 단계 미적용. 기존 MVP 실행 명령 main README 기준.
8. 원본·백업·비밀: main 기존 코드/SQLite 미수정, 쿠키/토큰/비밀번호/HAR 미수집.
9. 다음 작업: **현재 브랜드 비교 화면 스크린샷 1장** 받기 → DOM 대비 가시적 요소 확정 → 다음 UI 조작 하나씩.
10. 확인시각(KST): 2026-10-18 17:10:33; GitHub 파일 읽기 검증으로 범위 구분. 브라우저 E2E/Network 미검증.

## 브랜드 비교 화면 스크린샷 검증
1. **목표/스택:** 2026-10-18 17:14:41 KST, 젤네일 대시보드 관찰 전용 단계. 이전 FastAPI/SQLite 독립 MVP 2종 유지.
2. **관찰/결정:** 스크린샷 증거로 브랜드 비교 화면 상단에 수평 막대 차트 2개와 하단의 4개 브랜드 상세 테이블이 실재 표시됨을 검증. 오른쪽 NAILTOWN 선택과 무관하게 4개 브랜드 모두 비교 표시. 지수 EDGEU 결측은 0으로 간주 금지.
3. **테스트/검증:** 사용자 제공 `image(20261018-081243).png` 및 앞선 읽기 전용 DOM 결과 교차 확인. 화면 표시 성공; 별도 자동 클릭/API/Network/코드 빌드 검증은 미실행(기존 테스트 13/13 및 HTTP 6/6은 이전 결과).
4. **상태:** 브랜드 비교의 가시적 레이아웃 검증 완료; 상위 게시물 메뉴 및 실제 클릭·페이지 동작 미완료. 구현 시작 전 조사 지속.
5. **미확인/대안:** 차트 hover/click, 수요지수 공식, 데이터 API/정적 JSON, 다른 메뉴 복귀 시 태그 필터 보존 미확인. 변경 없는 차단 HTTP 재시도 금지; 사용자 탭 조작 후 스냅샷 검증.
6. **저장소/브랜치/SHA/경로:** `hibi89/astra_web_catcher` / `research/jp-nail-dashboard-20261018`, 연구 파일 `research/jp-nail-dashboard/BRAND_COMPARE_2026-10-18.md` 검증 커밋 `e8c0d5445a225a2cc7d43d9b116aa82b2f03da81`. main baseline `dd87ffc847c7b435c7eed7b4543b7db7d184e08c`.
7. **배포/실행:** 조사만 진행, Production/Vercel 미적용. 기존 두 MVP는 이전 README대로 로컬 실행.
8. **원본/백업/민감정보:** main 및 로컬 SQLite/테스트 변경 없음. 탭 제목 등 부가정보 포함될 수 있는 사용자 스크린샷을 GitHub에 복제하지 않고 관찰된 공용 대시보드 데이터만 기록. 쿠키/토큰/비밀번호 요청 금지.
9. **다음 작업/완료 기준:** 사용자에게 왼쪽 '상위 게시물'을 한 번 클릭하고 '눌렀어' 통보 요청. `#v-*` URL, 표 상위 게시물 개수, 정렬과 링크, 선택 브랜드 유지 여부 확인, 필요한 때만 스크린샷 요청.
10. **갱신(KST)/검증 범위:** 2026-10-18 17:14:41; GitHub 소스 재조회 및 수치·가시성 확인 완료, 차트 인터랙션/원본 네트워크는 미검증.

## 2026-10-18 — 상위 게시물 화면 실측

1. **목표·확정 요구·기술:** 일본 셀프 젤네일 대시보드 관찰과 독립 재구현 명세 수집, 사용자 요청에 따라 신규 앱 구현 보류. 별도 연구 브랜치에서 수행, 기존 FastAPI/SQLite MVP 두 종 변경 금지.
2. **완료 기능·결정:** 연결 탭 `#v-top`, 사용자 스크린샷에서 상단/우측 NAILTOWN 선택 유지, 총 20위 중 1~15 표기와 15행 실제 표시, 반응 내림차순·표 8열과 외부 링크·결측 표현 확인. 브랜드 비교는 4개 브랜드 표시, 상위 게시물은 선택 브랜드만 표시하는 UI 범위 차이 확인.
3. **테스트 명령·결과:** 사용자 스크린샷+읽기 전용 Browser tab text 비교. 현재 단계 자동 클릭/실제 링크 이동/API 호출/pytest 테스트 새로 실행하지 않음. 과거 API·HTTP 테스트 합격 기록은 유지하되 이번 관찰 검증과 구별.
4. **상태·중단 지점:** 상위 게시물 1페이지 시각·텍스트 관찰 완료, 페이지 2 직접 이동 전 대기. 아직 신규 앱 미구현.
5. **오류·원인·재시도 금지·대안:** 새로운 오류 없음. DOM 텍스트가 숨겨진 행까지 포함함을 확인; 시각적 가시성은 스크린샷 기준으로만 판정. 직접 서버 URL fetch 실패 반복 금지. API/정적 데이터·페이지 이동 로직·외부 링크 행동·산식 미확인.
6. **저장소·브랜치·SHA·경로:** `hibi89/astra_web_catcher` / `research/jp-nail-dashboard-20261018`; 연구 파일 `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md`, 검증 커밋 `ff4dfaccf7999a05b5304df06b52f4cb06b6a86e`; main 소스 기준 `dd87ffc847c7b435c7eed7b4543b7db7d184e08c` 유지.
7. **Production/실행 환경:** 조사 전용으로 배포 없음. 기존 로컬 MVP README 실행 방법 변경 없음.
8. **원본·백업·인증관리:** 두 MVP 소스·기존 데이터·테스트 변경 없음. 사용자 스크린샷은 별도 파일로 GitHub에 저장하지 않았으며 비밀·토큰·쿠키 등 공유/수집 안 함.
9. **다음 작업 우선순위·완료 기준:** 사용자에게 표 우상단 다음(›) **한 번만 클릭** 요청 → 스냅샷 재조회 → 16~20건/선택 브랜드/URL 비교 → 관찰 파일 갱신. 다른 메뉴 및 수식/연동 여부는 추후 단계.
10. **갱신 시각(KST)·검증 범위:** 2026-10-18 17:17:57; 스크린샷+연결 브라우저 텍스트+관찰 파일 GitHub 재조회. 신규 MVP 코드/브라우저 자동 E2E/Network 미검증.

## 2026-10-18 — 상위 게시물 다중 조작 결과: 원인 미확인
1. **목표/범위/기술:** 2026-10-18 17:23:40 KST 현재 일본 네일 대시보드 관찰 전용 단계, 별도 연구 브랜치; 기존 FastAPI/SQLite 두 MVP 변경 없음.
2. **변화/결정 근거:** 사용자가 여러 버튼 조작을 명시. 최종 브라우저는 `#v-top` 전체 KPI(153/526/101), 오른쪽 4브랜드 요약, 혼합 브랜드 Top 20 텍스트(표 1–15 / 20위). 단일 '다음' 버튼과 브랜드 변경의 인과관계 주장은 철회.
3. **테스트/검증:** 사용자 연결 브라우저의 읽기 전용 탭 재조회 1회. 동작별 클릭 추적·스크린샷·네트워크 요청·코드 테스트 미실행. 13개 이전 pytest와 6개 HTTP 테스트는 과거 결과.
4. **중단 지점:** 전체 브랜드 상위 게시물 1페이지로 보이는 최종 상태. 페이지 2 동작 미검증. 신규 대시보드 구현 시작 안 함.
5. **오류·원인·시도·대안:** 여러 조작이 섞여 전후 인과 판단 불가. 원본 사이트 오류라고 주장하지 말 것. 클릭 하나씩 분리하여 사용자 완료 메시지 후 DOM 확인.
6. **저장소/경로/SHA:** `hibi89/astra_web_catcher`, `research/jp-nail-dashboard-20261018`, `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md`; 정정 커밋 `5e2343f879aad9cda6b1a750d775cd3f09462dea`. Main 기존 SHA `dd87ffc847c7b435c7eed7b4543bdb7d184e08c`.
7. **Production/실행 환경:** 신규 앱 배포 미적용, 원본 연결 Chrome 읽기 전용. 기존 두 로컬 앱 실행법 변경 없음.
8. **원본/백업/인증:** `/shop`, `/jobs` 코드·기존 테스트·데이터 유지. 비밀/인증 토큰/쿠키/개인정보 미수집.
9. **다음 작업/완료 기준:** 현재 전체 상위 게시물 1페이지에서 표 우상단 `다음(›)`만 정확히 1회 클릭 → 메시지 → 화면 범위 16–20 여부 및 브랜드 유지 확인. 다른 메뉴로 넘어가지 않음.
10. **확인 시각(KST)/범위:** 2026-10-18 17:23:40 KST, 사용자 명시 + read-only 브라우저 DOM 및 GitHub 관찰 파일 재조회. 메뉴별 원본 API/수식 및 특정 클릭 이벤트 미검증.

## 2026-10-18 — 상위 게시물 2페이지 검증 확정

1. **목표/요구·기술:** 2026-10-18 17:26:29 KST 원본 일본 셀프 젤네일 사이트의 상위 게시물 페이지 전환 관찰; 별도 연구 브랜치, 기존 도서/채용 FastAPI MVP 보존.
2. **완료 내용과 결정:** 사용자의 단일 '다음' 클릭 결과, 화면 `16–20 / 20위`, 실제 5행(반응 1013/1012/963/900/875), 브랜드 '전체'와 오른쪽 4브랜드 패널 유지. Top 20의 15건 단위 페이지 이동 확인. 앞선 다중 조작 후 브랜드 변경 인과관계 혼란과 구별함.
3. **테스트·검증:** 첨부 `image(20261018-082517).png` 실제 가시 화면과 연결된 browser tab read-only DOM 텍스트의 `16–20 / 20위` 교차 확인. API 요청, 앱 테스트, 브라우저 클릭 자동화는 수행 안 함. 이전 13+6 테스트는 과거 기록.
4. **상태/중단:** 상위 게시물 페이지 이동 검증 완료. 다음은 페이지 2에서 브랜드를 바꿨을 때 페이지 초기화 확인 전. 신규 앱 미구현.
5. **실패/확인 안 된 사항:** DOM의 비가시 행 포함 위험으로 가시성은 스크린샷으로 판정. 원본 API vs 정적 데이터/DB/n8n 연동 및 계산식, 외부 링크 동작, 브랜드 변경 시 페이지 리셋 미확인. 동일 차단환경 재시도 불필요.
6. **저장소·브랜치·SHA·경로:** `hibi89/astra_web_catcher`, `research/jp-nail-dashboard-20261018`. 파일 `research/jp-nail-dashboard/TOP_POSTS_INITIAL_STATE_2026-10-18.md` 최신 근거 커밋 `2c9ec93d0beacf1f01ef390d5300d64c04f077b2`. 기존 main 기준 `dd87ffc847c7b435c7eed7b4543bdb7d184e08c`.
7. **Production/실행:** 현재 관찰 전용, 배포·서버 실행 없음. 기존 두 MVP 실행법은 main README.
8. **원본·백업·인증:** 두 앱과 SQLite 및 테스트 미수정. 화면의 데이터만 관찰, 인증 쿠키·토큰·개인정보/HAR 미수집.
9. **다음 작업·완료 기준:** 상위 게시물 2페이지 '전체' 상태에서 상단 OHORA를 **한 번만** 클릭하도록 안내. 클릭 후 URL/목록 행/브랜드/페이지 1 초기화 여부를 연결 탭에서 읽기. 다른 메뉴는 아직 하지 않음.
10. **갱신·확인 시각(KST):** 2026-10-18 17:26:29 KST, 사용자 스크린샷+브라우저 DOM+GitHub 커밋 후 재조회로 확인. 재구현 코드는 작성하지 않음.

## 2026-10-18 — OHORA 브랜드 변경 및 1차 관찰 마감
1. **목표·용도·확정 요구·기술:** 2026-10-18 17:32:53 KST, 기존 도서/채용 2개 MVP 유지하며 일본 젤네일 대시보드 동작 관찰 및 독립 DB/API 재현 설계. 새 앱은 미구현. 기술 후보 Next.js+TS+Prisma+SQLite(권고)/FastAPI+SQLite(대안); 승인 필요.
2. **완료·변경·근거:** 전체 Top 20의 2페이지(16–20위)에서 OHORA 클릭 시 OHORA 1페이지(1–15위)로 초기화됨. KPI 79/94/629/78, 우측 OHORA 지수 0.91, #v-top 유지. 앞선 대시보드/태그/브랜드 비교/상위 게시물 화면까지 관찰 완료. 검증 근거는 유저 조작 후 read-only 브라우저 스냅샷.
3. **테스트 명령·범위:** 연결 Browser list_tabs/get_tab_context 및 사용자 스크린샷 교차 확인; 원본 클릭 자동화, API/Network, 신규 앱 빌드/테스트 미실행. 역사적 도서·채용 pytest 13/13 및 HTTP 6/6 결과는 유지하되 이번 결과가 아님.
4. **완료/진행/대기/차단:** 네 화면 핵심 관찰/브랜드별 필터·페이지 상태 전환 완료. 계산·연동 미검증 목록을 독립 명세에 기록. 구현 시작은 기술안 승인 대기.
5. **오류·원인·시도·대안:** 추가 오류 없음. 예전 DNS 실패와 관리자 정책에 막힌 로컬 Chrome 환경 무의미하게 재시도하지 않음. 연결 브라우저 DOM은 숨겨진 행까지 보여 실제 가시성은 스크린샷 기준. UI 클릭 인과관계는 단일 조작일 때만 확정.
6. **저장소·브랜치·SHA:** hibi89/astra_web_catcher / research/jp-nail-dashboard-20261018; main dd87ffc847c7b435c7eed7b4543bdb7d184e08c 보존. 세부 근거 TOP_POSTS_INITIAL_STATE_2026-10-18.md 커밋 02f51a26b16098e3a4bb85931fc596f0890fbcea; 통합 OBSERVATION_CLOSEOUT_AND_MVP_SPEC_2026-10-18.md 커밋 a7366eb4485ad893cce5e88b4ef4cb2e950753f4.
7. **Production·URL·실행·환경:** 새 앱/배포 미적용. 원본 관찰 URL https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/; 기존 로컬 /shop, /jobs 실행 방법 main README 참조.
8. **원본·백업·인증:** main 원본·기존 SQLite 및 테스트/데이터 파일 건드리지 않음. 원본 사용자 비밀번호·인증 쿠키·토큰·민감 Network/HAR 수집 없음. 조사 스크린샷은 개인 탭 노출 위험으로 GitHub 업로드하지 않음.
9. **다음 작업·우선순위·절차·완료기준:** 다음 버튼 재시험 불필요. 기존 4 메뉴의 관찰 근거 및 미확인 항목은 통합 명세 참조. 사용자 A안(Next.js+TS+Prisma+SQLite) 또는 B안 승인 후 별도 폴더에서 DB/seed→API→UI→E2E·회귀 테스트. 원본 실행 보고서 버튼은 무단 실행 금지.
10. **갱신 시각·검증 범위·문서 기준:** 2026-10-18 17:32:53 KST. 브라우저 재조회 + GitHub 문서 read-back만 확인, 원본 Network/계산 코드·신규 앱 실행 미검증. 최신 문서 반영 커밋은 본 갱신 직후의 GitHub SHA.

## Nail Atlas B안: 로컬 구현·검증 완료 / GitHub 코드 미반영
1. **목표/요구/기술:** 2026-10-18 17:56:19 KST. B안 승인: FastAPI/SQLite/JS, 기존 쇼핑몰·채용 MVP와 독립 `nail_dashboard/` 서비스. 4개 메뉴, 브랜드·태그 필터, Top20 페이지네이션, 원본과 다른 계산 공식 구분, 실제 DB/API 사용. Docker/유료 서비스 없음.
2. **실제 구현/결정근거:** 로컬 18파일 소스와 샘플 SQLite 208 게시물/4 브랜드/30 태그. repository / metrics / app / static 완전 분리. 대시보드 집계·태그 5분류·전체 브랜드 비교·15+5 Top20, 브랜드 변경→page 1 리셋, 저장된 최신 보고서 재조회. 원본 성과지수 공식은 미확인, 게시물별 인덱스 null. 브랜드/태그 지수는 데모 공식임을 UI·README 명시.
3. **테스트 명령·성공/실패 수:** `python -m pytest -q nail_dashboard/tests/test_dashboard.py` 15 passed; `python -m nail_dashboard.tests.live_http_smoke` PASS(2 서버 프로세스 순차 실행 후 바이트 일치); `node --check nail_dashboard/static/app.js` PASS; `python -m compileall -q nail_dashboard` PASS; 직접 Uvicorn HTTP /nails 및 필터 API 모두 200, 잘못된 입력 422. 실제 브라우저 E2E 0회 성공/환경 차단(미검증). GitHub 테스트 파일은 아직 **없음**, 테스트 수행은 로컬 ZIP 재추출에서도 재검증.
4. **완료·대기·차단:** 로컬 기능+DB·API+테스트 문서 작성/실행 완료. 브라우저 자동 클릭 미검증. GitHub **코드 미반영**으로 프로젝트 기준 부분 완료; 새 대시보드 배포/실제 고객 데이터 연동 미실행.
5. **실패근거·재시도금지·대안:** git CLI remote `Could not resolve host: github.com`; 기존 npm/브라우저 차단과 구별. GitHub connector는 개별 text content 쓰기 가능하지만 컨테이너 코드 18파일을 바이너리/로컬경로 그대로 업로드하는 입력은 확인되지 않음. Playwright `Executable doesn't exist`; OS Chromium과 가상 라우트 모두 `ERR_BLOCKED_BY_ADMINISTRATOR`. 동일 방식 반복 불가. 대안: 다운로드 ZIP에서 안전한 브랜치로 소스만 로컬 커밋·push, 이후 GitHub에서 검증. 프론트 브라우저 테스트는 사용자 PC에서 수행.
6. **저장소·브랜치·SHA·경로:** `hibi89/astra_web_catcher`, 기존 `main` `dd87ffc847c7b435c7eed7b4543bdb7d184e08c` 그대로, 별도 문서 연구 브랜치 `research/jp-nail-dashboard-20261018`, 인수인계 보조문서 `research/jp-nail-dashboard/IMPLEMENTATION_AND_QA_2026-10-18.md` 커밋 `97436a163fb4357ee1eaf862a1c2fb3bd425e093`. 로컬 코드 nail_dashboard/schema.sql, db.py, repository.py, metrics.py, app.py, static/*, tests/*, README.md, TEST-REPORT.md, ARCHITECTURE.md, REVIEW-PACK.md (18파일).
7. **URL·실행·환경:** Production/Vercel 미적용. 저장소 루트 `python -m nail_dashboard.db seed`, `python -m uvicorn nail_dashboard.app:app --host 127.0.0.1 --port 8010`; `http://127.0.0.1:8010/nails` (로컬 서버 GET 200), JSON docs `/nails/api-docs`. Python 3.13/FastAPI 0.128/SQLite, JS/CSS.
8. **원본·백업·인증:** 기존 `/shop`, `/jobs` 및 data/app.db 테스트/소스 불변, 기존 테스트 이력 보존. 샘플 SQLite은 zip에 포함하고 GitHub에서 `.gitignore`로 제외. `seed`는 멱등, `--reset` 명시된 파괴적 옵션. 원본 사이트 코드/인증/비밀 미복제. 자체 공개 가상데이터만 쓰므로 이 신규 데모에는 회원 계정 없음. 외부 API 호출 없음.
9. **다음 작업·승인·완료 기준:** (우선) 이 채팅에서 제공한 ZIP sha256 `2bae267fbd8fd49b48db4597e898b699c4651c2d22ba13e7bc8b5650f92a1c11`를 보존해 별도 연구 브랜치의 `nail_dashboard/` 18파일로 GitHub 반영, DB 파일 제외; 코드 파일 재조회 및 커밋 SHA 확인 → 실제 로컬 브라우저 메뉴/필터/페이지 초기화 테스트 → 수정시 재회귀. 사용자 DB/API 연동은 데이터 구조가 제공되기 전 작업 금지.
10. **갱신(KST)·검증 범위:** 2026-10-18 17:56:19. 독립 ZIP 새 temp 폴더 추출 후 pytest 15/15+HTTP restart PASS+Node syntax PASS, 원본 main SHA 확인. Browser UI 차단 및 GitHub 코드 미반영 명확히 구분. 본 문서 커밋 SHA는 작성 후 별도 재조회로 확인.

## 2026-10-18 18:03 KST — nail_dashboard source verified in GitHub

1. Goal/stack: separate nail_dashboard FastAPI, SQLite, JS; existing shop/jobs preserved.
2. Implemented: four menus, DB-backed charts/KPI, brand/tag filters, 15+5 pagination and page reset, demo formula labels, saved report requery.
3. Tests: prior local pytest 15/15, Uvicorn HTTP restart PASS; remote source diff 18/18 PASS after GitHub push. Browser click E2E not verified.
4. State: code is now on remote research branch; user Windows runtime validation pending.
5. Former upload blocker: container DNS failure, resolved via GitHub Git Tree connector. No retry needed.
6. Repo/branch/source commit: hibi89/astra_web_catcher, research/jp-nail-dashboard-20261018, 93c15d0977bdff14788667de6a527f6d89426bd3. Paths: nail_dashboard/app.py, db.py, metrics.py, repository.py, static/, tests/.
7. Runtime: no production deployment; pip install -r requirements.txt, python -m nail_dashboard.db seed, python -m uvicorn nail_dashboard.app:app --port 8010; localhost:8010/nails.
8. Preservation: original main SHA dd87ffc847c7b435c7eed7b4543bdb7d184e08c unchanged; local SQLite data ignored by Git. No secrets uploaded.
9. Next: clone research branch into separate Downloads directory and test filters/page reset in a real browser; only fix issues with evidence.
10. Evidence timestamp: 2026-10-18 18:03 KST; remote branch verified and all 18 files read back. New code tests were not rerun after upload.

## 2026-10-18 18:18 KST — DB/API/JS regression verified 33/33

1. Goal / scope / technology: Preserve existing two MVPs and only regression-test isolated FastAPI/SQLite/vanilla JS nail_dashboard on research/jp-nail-dashboard-20261018. No source site extraction, no original index formula claims.
2. Completed functionality and changes: All four menus plus DB aggregation, category/brand filters, 15+5 Top20, selected-brand page reset, read-only report refresh. Newly corrected undefined 0/0 ratios: metrics returns null and JS renders dash, never fabricated 0%.
3. Test commands and counts: python -m pytest -q nail_dashboard/tests/test_dashboard.py => 33 passed in 1.33s (0 failed); python -m nail_dashboard.tests.live_http_smoke => PASS two actual Uvicorn processes and immutable SQLite file; python -m compileall -q nail_dashboard and node --check nail_dashboard/static/app.js => PASS. Existing tests and newly added cases use isolated temp DB.
4. Completed / in-progress / pending / blocked: SQL-versus-API KPI and weekly/hourly/content chart values checked, all brand comparison and category SQL joins checked, Top20 order, page reset contract, NULL/zero, empty dataset and zero denominator checked. User manually verified brand UI; real automated Chrome E2E still NOT executed.
5. Errors, evidence, attempts, alternatives: initial new zero-post test failed because positive_ratio(0,0)==0; patched return None, added JS percent null formatting, re-ran all 33 successful. Earlier sandbox Chromium administrator block remains known; do not repeat same blocked attempts. Node VM is a JS function test, not a rendered-browser proof.
6. Repo, branch, SHA, paths: hibi89/astra_web_catcher / research/jp-nail-dashboard-20261018, base main dd87ffc847c7b435c7eed7b4543b7d184e08c. Fix commit 4bc522c1f9110ad44f83d1e4b47ae0b5ce5ff87b, test commit 08ffe2f70f3d9bc2fd1e79edebe1aa3e0cd48e18, report commit 5796abe52ff54af91b009bbfe0b2dee5025af4bb. Key files nail_dashboard/metrics.py, static/app.js, tests/test_dashboard.py, TEST-REPORT.md.
7. Runtime and environment: no Vercel or production (not applicable). Python 3.13 tested in sandbox; from repo root pip install -r requirements.txt, python -m nail_dashboard.db seed, python -m uvicorn nail_dashboard.app:app --host 127.0.0.1 --port 8010, open http://127.0.0.1:8010/nails. Existing README includes all commands. Real Windows execution unverified.
8. Original and secrets management: Original /shop,/jobs, their data and tests untouched, main SHA unchanged. New DB tests use tempfile/pytest tmp_path, never local nail_dashboard/data/nails.db. No tokens, cookies, private user inputs or customer DB uploaded.
9. Priority next task / success criteria: If Windows QA is requested, run existing browser_e2e.py with Playwright installed; verify actual charts match API on browser, filter category page reset, error/console events. Fix only reproducible issues, preserve old tests; user must approve customer DB/API or deployment changes separately.
10. Last update and confidence: 2026-10-18 ~18:18 KST, verified in sandbox with actual SQLite, Python unit tests and actual HTTP restart; source files committed and fetched through GitHub. Browser layout, client device and production still unverified.

## Windows 실사용자 로컬 검증 보고 — 2026-10-18

1. **목표/확정 요구/기술:** B안 독립 FastAPI/SQLite 네일 대시보드의 Windows 로컬 테스트 확인; 기존 /shop·/jobs 보존.
2. **완료/검증된 동작:** 사용자 PC에서 DB 집계/필터/결측/분모0를 포함한 33개 pytest 전체 통과. 실제 Uvicorn HTTP startup, 200/422, stop/restart, SQLite 영속·불변 및 mellow 2페이지 5건 스모크 통과.
3. **실행 방법·결과:** `python -m pytest -q nail_dashboard/tests/test_dashboard.py` => 사용자 콘솔 `33 passed in 4.57s`; `python -m nail_dashboard.tests.live_http_smoke` => 사용자 콘솔 PASS 2줄. 실행 위치 Windows PowerShell 연구 브랜치 clone. 위 로그는 사용자가 직접 제공, ChatGPT가 Windows 실행을 원격 재현한 것이 아님.
4. **상태/중단 지점:** Windows API/DB 검증 완료. 렌더링된 네 메뉴의 차트·테이블·필터·페이지 초기화 Browser E2E 및 Console/Network 확인은 대기.
5. **오류/원인/시도/대안:** 이번 Windows 테스트에서 실패 0건; 신규 코드 수정 불필요. 앞선 ChatGPT 컨테이너 Chromium `ERR_BLOCKED_BY_ADMINISTRATOR`는 별도 환경 제약이며 Windows에 일반화하지 않음.
6. **저장소/브랜치/경로:** `hibi89/astra_web_catcher` / `research/jp-nail-dashboard-20261018`, `nail_dashboard/tests/test_dashboard.py`, `nail_dashboard/tests/live_http_smoke.py`, `nail_dashboard/TEST-REPORT.md`. GitHub 실 코드는 변경하지 않음.
7. **Production/환경/실행:** 배포 미적용, 로컬 `http://127.0.0.1:8010/nails` 사용. 사용자 PC에서 서버 재시작/HTTP 스모크 통과. 원본 서비스/API/n8n 미연동.
8. **원본·백업·보안:** main 및 두 기존 MVP, 기존 SQLite 데이터 미수정. 테스트는 독립 데이터 사용; 새 코드·개인정보·비밀 업로드 없음.
9. **다음 우선 작업/완료 기준:** 실제 Windows Chrome에서 4메뉴 렌더링, 브랜드 변경·태그 컬러, Top20 2페이지→브랜드 변경 1페이지 초기화, 데이터·API 일치 및 Console/Network 확인. 오류 증거가 있는 기능만 최소 수정.
10. **기록 기준:** 2026-10-18 KST, 사용자 제출 콘솔 원문 확인; Windows UI/Console/Network는 확인 부족으로 미검증. 본 HANDOFF 최신 문서 커밋은 GitHub 읽기 재검증 필요.

## 2026-10-18 — Windows Playwright 색상 필터 대기 실패 대응

1. **목표/요구/스택:** Windows 실제 Playwright E2E 8행 AssertionError 재현 보고 대응, 독립 `nail_dashboard` FastAPI/SQLite/JS. 기존 두 MVP 미수정.
2. **변경/근거:** 기존 `browser_e2e.py`는 `[data-category=color]` 클릭 직후 데이터 재로딩 대기 없이 동기 `count()==8`. `static/app.js`의 비동기 fetch 후 DOM 렌더로 인한 race 가능성이 높아 Playwright `expect(...).to_have_count(..., timeout=15s)`로 수정. 모든 메뉴/페이지 click 뒤 같은 대기를 적용. 앱 자체 변경하지 않음.
3. **테스트 결과:** 사용자 원본 Windows Playwright는 색상 필터 검증 assertion에서 FAIL; 설치 성공. 변경 코드의 별도 컨테이너 Python compile PASS, `python -m pytest -q nail_dashboard/tests/test_dashboard.py` 33/33 PASS, `python -m nail_dashboard.tests.live_http_smoke` PASS. **수정된 Windows Chrome 실제 E2E는 아직 미검증**.
4. **진행 상태:** 원본 UI 동작 오작동 vs 타이밍 문제를 새 테스트 실행으로 구분할 단계; 기존 사용자 Windows pytest/HTTP PASS 이력 유지.
5. **실패/원인/재시도 제한:** 첫 예외에서 실제 행수 미출력이라 기능 버그 확정 불가; 테스트 불충분. 수정본은 실패시 URL, 행수, 일부 내용, JS/API 오류 출력. 환경 차단된 동일 샌드박스 Chromium 방식 무의미한 재시도 금지.
6. **저장소/브랜치/코드 SHA:** `hibi89/astra_web_catcher`, `research/jp-nail-dashboard-20261018`; `nail_dashboard/tests/browser_e2e.py` 수정 커밋 `8f50fb9b01460d9f2e98b526978237c19f5ebffc`. main 도서/채용 MVP 보존.
7. **실행/URL/환경:** 프로젝트 루트에서 `python -m uvicorn nail_dashboard.app:app --port 8010` 서버 유지, 다른 터미널에서 `git pull --ff-only`, `python -m nail_dashboard.tests.browser_e2e`; 로컬 `http://127.0.0.1:8010/nails`.
8. **기존 데이터/보안:** 배포/외부 API·사용자 DB 연결 없음. 기존 SQLite 데이터 및 기존 두 MVP 보존. GitHub에는 E2E 테스트 파일만 수정.
9. **다음 작업/완료 기준:** 사용자 PC에서 개선된 E2E 재실행, 메뉴/컬러/브랜드 비교/Top20 페이지/브랜드 변경/JS 오류가 PASS일 때 브라우저 검증 완료로 판정. 실패 시 새 로그 기준 app.js나 테스트를 선택적으로 수정하고 33/33과 HTTP 회귀 재검증.
10. **시각/검증범위:** 2026-10-18 KST 사용자가 보내준 최초 Windows Traceback으로 근거 확보. 수정된 테스트 파일 GitHub 재조회, 단위/HTTP 재검증; 실제 Windows 개선본 실행 대기.
