# P4 — 합성 소유자 API 기반 클라이언트 Chart/Table

일자: 2026-10-19 KST
기준: codex-p4-20261019 / b3166b67604381a9d2afd41667b65f9a9b103b37

## 범위

기존 owner isolation API가 소유자별 합성 SQLite 데이터를 반환하는 기능은 유지하면서, 새 /client-preview 경로를 추가했다. 이 경로의 HTML은 데이터가 없는 셸이며 브라우저가 동일 출처의 /api/demo/series를 호출해 응답을 검증한 뒤 SVG 차트와 테이블 DOM을 만든다. 기존 /preview 서버 렌더링 경로도 그대로 동작한다.

데이터는 examples/p4_owner_demo_schema.json과 examples/p4_owner_demo_rows.json의 전부 합성된 값이다. 공유 SQLite :memory: DB에 저장하며, 모든 조회에 서버에서 세션 쿠키로 확인한 owner_id 조건을 적용한다. 로그인·세션 발급 HTTP API, 쓰기 API, 실제 소유자 DB 연결은 없다.

## 응답 검증과 화면 동작

- 브라우저는 셸에 포함된 예상 소유자, 데이터셋, 행 개수, 스냅샷 SHA-256, 4개 명시적 필드 바인딩과 API 응답을 대조한다.
- API 상태, 응답 필드, 승인 상태, 데이터 형식, 날짜, 유한 숫자, 중복 entity/period 키, 행 개수와 전체 행 스냅샷 해시가 모두 맞아야 렌더링한다.
- SHA-256은 표준화한 전체 JSON 행의 해시를 HTML 셸의 기대 해시와 비교한다. 해시가 바뀐 응답이나 행과 자체 해시를 함께 바꾼 응답도 거부한다.
- 새 요청은 이전 화면을 지우고 순번을 높인다. 오래된 응답이 나중에 도착해도 최신 요청의 오류나 데이터를 덮지 않는다. 같은 이벤트 턴의 중복 버튼 클릭은 한 번만 요청한다.
- 네트워크 실패, 소유자 불일치, 무결성 실패는 데이터를 지우고 구분 가능한 상태 문구를 보여준다. 실패 뒤 재시도는 정상 응답으로 복구된다. 유효한 빈 응답은 별도의 빈 상태로 처리한다.
- 전환 버튼은 마우스와 키보드 Enter/Space/좌우 화살표로 조작할 수 있다. 320, 390, 768, 1366 CSS 픽셀 너비를 실제 Chromium으로 확인했다.
- 표와 SVG는 textContent와 DOM API로 작성한다. 외부 스크립트, CDN, 이미지, 외부 API 요청은 사용하지 않는다. CSP는 script를 same-origin으로 한정한다.

## 파일

- astra_contracts/synthetic_owner_isolation.py — 기존 API/서버 렌더링을 보존하고, 데이터 없는 client shell과 same-origin JS asset을 추가했다. 비어 있는 demo owner는 새 선택 인자에서만 허용한다. 기존 기본 검증은 소유자별 fixture가 비면 계속 거부한다.
- astra_contracts/owner_client_chart_table.js — 응답 검증, 해시 확인, 상태 관리, 요청 순번 차단, 차트·표 DOM 구성 및 전환 조작.
- tests/test_owner_client_chart_table.py — client shell/API 응답, 격리, CSP, 빈 상태, 기본 입력 거부 확인.
- scripts/p4_owner_client_chart_table_browser_smoke.py — 실제 loopback HTTP와 Chromium E2E.
- .github/workflows/p4-owner-isolation.yml — 새 Python 테스트와 Chromium E2E를 기존 전체 회귀 workflow에 추가했다.

## 실제 실행 결과

- 신규 client 계약 7개, 기존 owner 격리 33개, 기존 SQLite/API 13개: **53/53 PASS**, 경고 1개(설치한 최신 Starlette의 TestClient/httpx deprecation 경고).
- node --check astra_contracts/owner_client_chart_table.js: **PASS**.
- python -m compileall -q app astra_contracts scripts tests: **PASS**.
- 실제 Windows loopback HTTP + Chromium 156.0.8078.4: **PASS**. A/B 계정 각 3행 렌더링, 404 교차 owner, 빈 owner, 요청 실패 후 복구, 다른 owner 응답 거부, API 행 변조 거부, 지연된 이전 owner 응답 무시, 같은 턴 중복 요청 합치기, 키보드 전환, 반응형 화면, XSS 문자열 text-only, JavaScript 예외 0건, 외부 요청 0건을 확인했다.
- 교차 owner 검증의 의도된 HTTP 404 1건과 재시도 시뮬레이션의 의도된 네트워크 실패 1건은 브라우저 증거에서 별도 분류했다. 예상되지 않은 Console 오류는 0건이다.
- 전체 저장소 명령을 로컬 Windows에서 실제 실행했다: Python 3.12.14, UTF-8 모드, workspace 의존성, selenium 설치, 허용된 별도 TEMP 경로, Python을 PATH에 추가하고 `python -m pytest -q -ra --tb=no tests` 실행 결과 **752 passed, 96 failed, 108 errors, 3 skipped, 2 warnings**. 따라서 전체 회귀는 **통과하지 않았다**. 당시 per-test JUnit/log는 저장되지 않았고 `.pytest_cache/v/cache/lastfailed`는 Windows 및 WSL에서 권한 거부되어 96/108의 정확한 테스트별 분포는 복구하지 못했다.
- 2026-10-19 최소 범위 재검증: 로컬 Python 3.11.9 / pytest 9.1.1 / FastAPI 0.143.3 / Starlette 1.8.0 / httpx 0.28.1에서 다음 명령을 실행했다.

  `& 'C:\Users\haein\AppData\Local\Programs\Python\Python311\python.exe' -m pytest -q -ra --tb=short -p no:cacheprovider tests/test_owned_migration_schema.py::test_exact_repository_migration_blob tests/test_synthetic_generator.py::test_symlink_destination_refused tests/test_synthetic_generator.py::test_generated_app_passes_its_own_pytest_and_persists_demo_sqlite`

  종료 코드 1, **3 failed / 20.94s**. Migration blob 검증은 기대 `5f5bdcb950dcfa0587b0deec2b7afb5e17f155bd`, 작업 파일 bytes에서 계산한 `ab965a6f889db3c167ebdccf561ef47bc3955256`로 불일치했다. `git config core.autocrlf=true`; `git ls-files --eol migrations/001_initial.sql` 결과 `i/lf w/crlf`라 테스트가 CRLF working bytes를 직접 해시하는 환경 원인이 확인됐다. Symlink 재현은 generator 호출 전에 `OSError: [WinError 1314]`로 실패하여 테스트 capability setup이 막혔다.
- 같은 생성 앱 하위 pytest는 plugin autoload를 끈 상태에서도 18초 timeout을 재현했다. `-vv -s` 출력은 테스트 수집 후 `test_health_list_filter_search_detail`에서 멈췄다. 추가 대조로 DB 없는 `FastAPI()` + `TestClient.get('/')`도 client 생성 뒤 8초 timeout이 났다. 따라서 이 재현은 프로젝트 SQLite lock 증거가 아니다. 이전 문서의 “subprocess SQLite file lock” 원인은 현재 보유한 로그로 확인하지 못해 미확정으로 낮춘다. timeout의 구체 원인도 이 단위에서 확정하지 않았다.
- 기존 전체 실행의 3 skip은 두 pinned OWID archive 부재와 한 Windows symlink capability skip으로 문서화되어 있다. 이 대표 검증은 aggregate 96/108 전체를 분류하지 않으며, 이를 코드 결함이나 환경 문제로 일괄 판정하지 않는다. 패키지 다운로드나 외부 서비스 연결은 하지 않았다.
- 기준 커밋의 과거 940 PASS / 2 SKIP 및 GitHub Actions 39225637124 결과를 이번 코드의 새 결과로 재사용하지 않는다.
- 새 workflow는 수정했지만 push 제한으로 GitHub Actions를 새로 실행하지 않았다. 이 결과 문서의 Chromium PASS는 로컬 Windows에서 직접 실행한 결과다.
- Linux 재검증 경로도 확인했다. Ubuntu WSL은 실행되지만 Python 3.14.4에 `pip`, `ensurepip`, `pytest`가 설치되어 있지 않았다. `/mnt/c` checkout의 Windows `.git` worktree pointer는 기본 Linux Git 경로로 유효하지 않지만 `GIT_DIR`/`GIT_WORK_TREE` 지정으로 HEAD 조회는 가능했다. Docker CLI에는 실행 중인 daemon이 연결되지 않았다. 이 환경에서 Linux 전체 suite는 실행하지 않았으며, package registry나 외부 서비스를 호출하지 않았다.
- 별도로 Linux 구문 검증 `PYTHONPYCACHEPREFIX=/tmp/astra-p4-pycache python3 -m compileall -q app astra_contracts scripts tests`를 WSL에서 실행해 **PASS**를 확인했다. 이는 pytest 전체 회귀나 Chromium E2E 결과를 대신하지 않는다.

## 권한과 해석의 한계

모든 수치와 계정은 발명한 테스트 값이다. 구조적 필드 매핑은 검토 전이며 mapping_approved=false, owner_schema_connected=false, generation_authorized=false, deployment_authorized=false, generation_contract=blocked_pending_review를 유지한다.

이 SHA 대조는 같은 출처의 API 응답과 셸 스냅샷 간 불일치 검출을 위한 것이다. SHA-256 자체가 응답 서명이나 인증 수단은 아니며, HTML 셸과 API가 함께 변조되는 상황을 방어한다고 주장하지 않는다. 실제 고객 환경 보안, 원래 사이트 계산 의미, 상용 정확성, 배포 적합성은 입증하지 않는다.

재현 명령:

~~~~powershell
python -m pip install -r requirements.txt 'selenium>=4.27,<5'
python -m pytest -q -ra tests/test_owner_client_chart_table.py tests/test_synthetic_owner_isolation.py tests/test_synthetic_sqlite_dashboard.py
python -m playwright install chromium
python -m scripts.p4_owner_client_chart_table_browser_smoke --schema examples/p4_owner_demo_schema.json --rows examples/p4_owner_demo_rows.json
~~~~
