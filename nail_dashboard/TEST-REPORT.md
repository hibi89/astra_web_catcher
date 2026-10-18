# Nail Atlas Test Report — 2026-10-18 (KST)

## 실제 실행

| 검증 | 명령 | 기대 | 실제 결과 | 판정 |
|---|---|---|---|---|
| API·집계·필터·보존·권한 입력 검증 | `python -m pytest -q nail_dashboard/tests/test_dashboard.py` | 모든 API 일관·임시 DB 독립 | **15 passed in 0.73s** | PASS |
| Python 구문 | `python -m compileall -q nail_dashboard` | 오류 없음 | 종료 0, 출력 없음 | PASS |
| JavaScript 구문 | `node --check nail_dashboard/static/app.js` | 오류 없음 | 종료 0, 출력 없음 | PASS |
| DB 시드 | `python -m nail_dashboard.db seed` | 가상 게시물/태그 저장 | `208 posts`, `4 brands`, `30 tags` | PASS |
| 실제 Uvicorn 서버 + HTTP 요청 | uvicorn 127.0.0.1:8010 + httpx GET | HTML/JS/API 200 | `/nails`, JS, latest, overview, posts(page2), tags(color) 모두 **200** | PASS |
| 프로세스 재시작·영속·읽기 전용 | `python -m nail_dashboard.tests.live_http_smoke` | 세션이 아닌 DB 기반 조회 일치 | 두 서버 프로세스 순차 시작/종료, `/nails` 200, 유효 조회 200, 잘못된 입력 422, 재시작 전후 동일 응답, SQLite 파일 바이트 불변 | PASS |
| 브라우저 자동 조작 | Playwright Chromium (기본 내장 브라우저) | 4메뉴 필터/페이지 UI 확인 | 브라우저 실행 파일 누락 | 미실행 |
| 브라우저 자동 조작 대체 | 시스템 `/usr/bin/chromium`로 localhost 탐색 | 로컬 화면 열림 | `Page.goto net::ERR_BLOCKED_BY_ADMINISTRATOR` | 환경 차단 |
| 격리 라우트 브라우저 검사 | 요청 라우트를 자체 FastAPI TestClient 결과로 fulfill | 외부 네트워크 차단 영향 제거 | `Page.goto net::ERR_BLOCKED_BY_ADMINISTRATOR` | 환경 차단 |
| 실제 사용자 Windows 브라우저 | `python -m nail_dashboard.tests.browser_e2e` | UI 클릭 및 JavaScript runtime 확인 | 이 환경에서는 미실행 | 검증 대기 |

## 테스트 15개 목록 및 판정

1. `test_route_and_assets` PASS — 정적 파일과 HTTP 화면
2. `test_report_refresh_read_only` PASS — 최신 보고서 조회 API가 DB 파일을 변경하지 않음
3. `test_fictional_sample_and_db_counts` PASS — KPI를 DB SQL 수량과 교차 검증
4. `test_brand_filter_aggregation_matches_sqlite` PASS — 브랜드별 분석 게시물 일치
5. `test_brand_compare_is_global` PASS — 4브랜드 비교 불변
6. `test_tags_category_filter_and_counts` PASS — 컬러 8개·전체 30개, 정렬
7. `test_tags_pagination` PASS — 14개씩 페이지
8. `test_posts_top20_and_15_5_pages` PASS — 15건+5건·반응순 정렬
9. `test_post_brand_filter_and_page_reset_contract` PASS — API 브랜드 20건과 UI `page=1` 리셋 핸들러 정적 검사. 실제 브라우저 클릭은 미검증
10. `test_post_rank_and_null_semantics` PASS — 조회수 NULL/숫자 0 및 미구현 성과지수 구분
11. `test_invalid_filters_and_pages` PASS — 잘못된 브랜드/카테고리/페이지 422
12. `test_missing_db_is_service_unavailable` PASS — DB 없음 503·웹 화면 표시
13. `test_seed_idempotent_and_reload` PASS — 기존 시드 보존·다른 앱 인스턴스 동일 결과
14. `test_db_seed_unique_links_and_schema` PASS — 참조 무결성 및 링크 중복 없음
15. `test_formulas_do_not_claim_original` PASS — 데모/미구현 경고 표시

## 제외/한계

- 이번 새 대시보드는 개인계정 데이터가 없는 가상 공개형 데이터 시연이므로 회원가입/인증·A/B 사용자 격리는 대상이 아님. 이전 두 MVP의 인증 테스트를 새 프로젝트 PASS로 합산하지 않음.
- UI 클릭을 **자동 브라우저에서 통과했다고 주장하지 않음**. `browser_e2e.py`는 사용자의 일반 PC에서 검증할 수 있도록 포함한 미실행 테스트임.
- 프로덕션/Vercel 미적용, n8n·Instagram·사용자 DB/API 미연동.
- 원본 사이트 수요/성과지수의 계산식 미확인; 명시된 demo ratio만 구현, 게시물별 성과지수 미구현.
\n## Regression verification 2026-10-18 18:17 KST

- Scope: 15 existing and 18 extended SQL/API/state cases. Every pytest case uses its own SQLite DB under pytest tmp_path, not the development database.
- Executed: python -m pytest -q nail_dashboard/tests/test_dashboard.py
- Actual result: 33 passed in 1.33s; 0 failures.
- Executed: python -m nail_dashboard.tests.live_http_smoke
- Actual result: PASS HTTP startup, page/API 200, invalid request 422, two complete Uvicorn stop/start cycles, stable results, unchanged SQLite database bytes; brand=mellow page2 returned 5 items.
- Executed: python -m compileall -q nail_dashboard and node --check nail_dashboard/static/app.js; both exit 0.

| Test case / execution | Expected | Actual | Status |
|---|---|---|---|
| KPI and weekly chart (all + four brands, 5 test cases) | SQLite post/brand counts, reels, response averages and 13 weekly series equal API | Equal per stored SQL rows | PASS |
| Time/content/type charts (three scopes, 3 cases) | Recompute hourly median, format mean/count, direct vs sheet totals | All returned chart points equal independent Python calculations | PASS |
| Brand comparison | Four brand medians, analyzed/collected counts and view coverage equal stored SQL | Equal; comparison remains global | PASS |
| Tag categories and filter scope | 5 categories equal SQL post_tags joins, 8 color tags, global demo table | Equal | PASS |
| Top posts and pagination | Reaction DESC Top20 for all/four brands with 15+5 pages | All five scopes matched IDs/order/count | PASS |
| Data modification | Raise one test-record likes by 90000, rebuild aggregates | Mean KPI, format chart and Top1 changed appropriately | PASS |
| Empty post table | Empty/zero chart results, nullable undefined ratios | No crash, undefined ratio null, list empty | PASS |
| Zero reaction baseline and zero prior 8 weeks | No division error or false ratio | Brand/tag indices and 4v8 null | PASS |
| Missing values | views=0 distinct from SQL NULL, unimplemented performance index null | Correct | PASS |
| Report not seeded | Structured error | HTTP 503 with seed guidance | PASS |
| UI page reset function | Executed actual JS chooseBrand in Node VM on page 2 | URL brand=mellow and page=1, null formatting dash | PASS |

Initial additional-test failure: test_empty_posts_yields_null_ratios_and_zero_charts found positive_ratio(0,0) returned numeric 0. Corrected metrics.positive_ratio to return None for denominator 0, and JS percent helper to display '—' rather than 0% or —%. Retested 33/33 PASS. Valid denominators retain previous behavior.

Important boundary: Node VM executes a real JS state function but is not Chrome. Playwright visual E2E/CSS/Console/network was NOT run. User directly verified browser brand changes separately. Source demand/performance formulas remain unverified and demo-only; external user data/Instagram/n8n integration NOT completed.

## Windows 실사용자 로컬 검증 보고 — 2026-10-18

사용자가 Windows PowerShell에서 이 저장소의 최신 연구 브랜치를 받은 후 실행한 **실제 콘솔 출력**을 대화로 전달함. 실행은 사용자 PC에서 이루어졌으며 ChatGPT가 해당 PC의 프로세스를 직접 관찰하거나 로그 파일을 취득한 것은 아님.

- 실행 명령: `python -m pytest -q nail_dashboard/tests/test_dashboard.py`
- 실제 사용자 출력: `33 passed in 4.57s` (`[100%]`). 0개 실패.
- 실행 명령: `python -m nail_dashboard.tests.live_http_smoke`
- 실제 사용자 출력: `PASS HTTP startup + /nails + 200 API + validation 422 + process stop/restart + persistent SQLite + no mutation`.
- 실제 사용자 출력: `PASS brand=mellow page2 rows 5`.
- Windows 환경에서 테스트/실서버 스모크가 성공함을 확인하는 **사용자 실행 근거**. 앞선 격리 컨테이너의 33 PASS 및 스모크 결과와 구분해서 기록.
- 여전히 미검증: 네 메뉴 전체의 Windows 브라우저 자동 E2E, 렌더링 차트 숫자와 API 응답 일치, Console/Network 에러. 사용자가 브랜드 전환 시 UI 연동을 수동 확인한 결과는 별개.

## 2026-10-18 — Windows Playwright 색상 필터 대기 실패 대응

- 사용자 Windows에서 Playwright Chromium 다운로드/설치 성공(Chromium v1248). `python -m nail_dashboard.tests.browser_e2e` 최초 실행 시 태그 전체(14개) 검사를 통과한 뒤 `[data-category="color"]` 클릭 직후 `assert page.locator('tbody tr').count()==8`에서 AssertionError 발생. 실제 행 수/JS 오류 상세는 기록되지 않았으므로 색상 필터 기능 결함으로 단정하지 않음.
- 원인 후보 및 근거: `static/app.js`는 클릭시 비동기 API `/api/nails/tags?category=color`와 재렌더를 수행하지만 기존 브라우저 테스트는 후속 `count()==8`을 즉시 검사해 DOM 갱신을 기다리지 않음. 기존 SQL/API pytest에서는 컬러 8행을 별도 확인.
- 개선: `nail_dashboard/tests/browser_e2e.py`의 즉시 `assert count`를 Playwright `expect(locator).to_have_count(..., timeout=15000)`로 변경. 다른 화면 이동과 15→5→15행까지 전환 후 조건 대기. 페이지 URL 해시/쿼리, 컬러 활성, 브랜드 aria-pressed, JS pageerror 및 API HTTP 400+ 수집. 실패 시 URL/행수/화면 일부/오류 출력. 실 서버/앱 기능 로직은 변경하지 않음.
- 코드 커밋: `8f50fb9b01460d9f2e98b526978237c19f5ebffc`; GitHub 파일 재조회 내용 검증 완료.
- 수정 작업 환경에서 `python -m py_compile nail_dashboard/tests/browser_e2e.py` PASS; `python -m pytest -q nail_dashboard/tests/test_dashboard.py` **33/33 PASS**; `python -m nail_dashboard.tests.live_http_smoke` PASS; Node JS 구문 이전 검사 PASS.
- **미검증:** 수정 버전의 실제 Windows Playwright 브라우저 E2E 완료 여부. 동일 환경에서 재실행을 받아 PASS/FAIL 판단할 것. 비동기 대기 보강으로 고쳤다고 확정적으로 말하지 말 것.
