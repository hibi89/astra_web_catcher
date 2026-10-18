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
