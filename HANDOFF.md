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
