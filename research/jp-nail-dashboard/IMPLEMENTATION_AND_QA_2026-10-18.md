# Nail Atlas B안 — 구현/검증 결과 및 소스 인수인계 (2026-10-18 KST)

## 범위와 상태
- 사용자 승인: B안 FastAPI + SQLite, **기존** /shop · /jobs 메인 소스와 두 MVP 테스트 변경 금지, 신규 `nail_dashboard/` 디렉터리.
- **실제로 별도 실행 컨테이너에 신규 소스 18개 파일 구현 및 실행**. 단, 이 문서 작성 시 GitHub에 신규 `nail_dashboard/` **소스 파일 자체는 아직 미커밋**. GitHub 브랜치에 코드가 있다고 주장하지 말 것.
- 현재 소스 전체는 이 채팅에서 생성한 `Astra_P4_Nail_Atlas_B_MVP_2026-10-18.zip` (62,821바이트, sha256 `2bae267fbd8fd49b48db4597e898b699c4651c2d22ba13e7bc8b5650f92a1c11`) 다운로드 파일 안에 보관. 실행 패키지에 가상 seed SQLite DB 포함.
- 이후 GitHub 코드 반영 완료 전까지 **부분 완료(로컬 검증 완료 / GitHub 코드 미반영 / 실제 브라우저 자동 E2E 미검증)**.

## 실제 구현 파일 및 데이터 흐름
- `nail_dashboard/schema.sql`: ReportRun·Brand·Post·Tag·PostTag 및 인덱스/제약.
- `nail_dashboard/db.py`: 가상 4브랜드 / 208 게시물 / 30 태그 deterministic seed; 기본 기존 DB 보존, `--reset`일 때만 삭제.
- `nail_dashboard/repository.py`: SQLite 조회 어댑터. 사용자 DB/API로 교체 가능하게 별도 분리.
- `nail_dashboard/metrics.py`: 순수 집계, KPI/주별/시간별/콘텐츠 유형/태그·브랜드 지수 데모 함수.
- `nail_dashboard/app.py`: Read-only FastAPI; `/nails`, `/api/nails/reports/latest`, `brands`, `overview?brand=`, `tags?category=&page=`, `brands/compare`, `posts?brand=&page=`.
- `nail_dashboard/static/index.html`, `app.js`, `style.css`: 4메뉴·선택 브랜드·태그 분류·15+5 페이지네이션·페이지 1 초기화·URL 상태·로딩/오류/빈 값.
- `nail_dashboard/tests/test_dashboard.py`, `live_http_smoke.py`, `browser_e2e.py`: 테스트.
- `nail_dashboard/{README,ARCHITECTURE,TEST-REPORT,REVIEW-PACK}.md`: 실행·기술·검증·인수인계.
- JS에 숫자 배열 하드코딩하지 않음. SQLite 저장값 → repository → metrics → FastAPI JSON → 화면.
- 원본 반응·태그·4주 수식 복제하지 않음. 자체 demo 공식만 명시; 게시물별 성과지수 null/미구현. '최신 보고서'는 **저장된 DB를 다시 GET**(수집 안 함).
- 사용자 자신의 API/DB **아직 미연동**, 원본 API·정적 JSON 여부 **미확인**, 태그-브랜드 원본 미확인 범위는 독립 계약으로 명시.

## 실제 검증 근거
- `python -m pytest -q nail_dashboard/tests/test_dashboard.py` → **15 passed in 0.77s** (검증된 ZIP을 새 임시 디렉터리에 풀고도 다시 통과).
- `python -m nail_dashboard.tests.live_http_smoke` → **PASS**. 실제 Uvicorn 신규 프로세스 → API·HTML 200/잘못된 페이지 422 → 정상 종료 → 재시작 → 데이터 및 DB 파일 바이트 불변.
- `node --check nail_dashboard/static/app.js` → PASS.
- `python -m compileall -q nail_dashboard` → PASS.
- 직접 Uvicorn /nails, JS, report, overview, posts(2페이지), tags(color) HTTP 요청 각각 200.
- Chromium Playwright 기본 브라우저 실행 파일 누락 → 시스템 Chromium 사용하여 `Page.goto net::ERR_BLOCKED_BY_ADMINISTRATOR` → 네트워크 라우트 응답 우회 없이 로컬 ASGI 응답을 동일 브라우저에 제공하는 모의 주소 라우팅도 동일 정책 차단. 무의미한 반복 중지. **브라우저 클릭 E2E 미검증**이며 사용자가 직접 검증해야 함.
- 기존 쇼핑몰/채용 13/13·추가 HTTP 6/6은 이전 결과; 새 대시보드 테스트와 합산하지 않음.

## 설치·실행 / 후속 GitHub 반영
1. 채팅의 최종 ZIP 다운로드 후 빈 폴더 또는 `hibi89/astra_web_catcher` 저장소의 체크아웃에 압축 해제. 기존 소스 덮어쓰지 않도록 반드시 `nail_dashboard/`만 추가하는지 확인.
2. 저장소 루트에서 `python -m pip install -r requirements.txt`, `python -m nail_dashboard.db seed`, `python -m uvicorn nail_dashboard.app:app --host 127.0.0.1 --port 8010`.
3. 브라우저 `http://127.0.0.1:8010/nails`.
4. 테스트 `python -m pytest -q nail_dashboard/tests/test_dashboard.py` 및 `python -m nail_dashboard.tests.live_http_smoke`.
5. source GitHub 반영은 아직 필요. 대상 별도 브랜치 `research/jp-nail-dashboard-20261018`; **아직 반영되었다고 주장하면 안 됨**. 채팅 ZIP은 영구 Git 버전 보존 대체물이 아님.
6. `nail_dashboard/data/nails.db`는 GitHub 업로드 금지(`.gitignore`). 개발·사용자 데이터 덮어쓰기 금지.

## 완료 판정
- **로컬 코드/DB/HTTP/pytest:** 통과.
- **프론트 브라우저 클릭 / Production:** 미검증/미적용.
- **GitHub 실제 코드 18파일:** 미반영, 후속 체크인 필요.
- **현재 고객 DB/API 연동:** 미연동.

## 후속 정정: GitHub 소스 반영 완료 (이 절이 앞선 '미반영' 기록보다 최신)

- 2026-10-18 18:03:24 KST, 코드 18개를 기존 main이 아닌 `research/jp-nail-dashboard-20261018` 브랜치의 `nail_dashboard/`에 한 번의 트리 커밋으로 추가.
- 실제 코드 커밋 SHA: `93c15d0977bdff14788667de6a527f6d89426bd3`; GitHub branch HEAD 갱신·재조회 확인. **18/18 파일 전체 소스 읽기 후 매니페스트와 내용 일치**.
- 이전 문서의 'GitHub 미반영'은 당시 상황을 기술한 이력으로 남지만, 현재 상태는 **소스 반영 완료**다.
- 기존 main의 /shop, /jobs, 데이터, 테스트는 불변; 신규 SQLite .db 파일은 GitHub 커밋에 포함하지 않았다.
- 설치: GitHub 브랜치 직접 clone 후 `python -m pip install -r requirements.txt`, `python -m nail_dashboard.db seed`, `python -m uvicorn nail_dashboard.app:app --port 8010`.
- 자동 pytest 15/15, 실제 Uvicorn/DB 재시작, JS 구문 등은 **이전에 검증한 동일 소스 결과**이며, 이번 GitHub 업로드 과정에서 재실행하지 않았다. 사용자 Windows 브라우저 클릭 E2E는 계속 미검증.
- 본 문서 및 HANDOFF/STATUS 후속 문서 커밋으로 브랜치 HEAD는 위 코드 커밋보다 진전할 수 있으나 코드 18파일은 동일하다.
