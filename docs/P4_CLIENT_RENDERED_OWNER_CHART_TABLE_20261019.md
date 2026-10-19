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
- 전체 저장소 명령을 로컬 Windows에서 실제 실행했다: Python 3.12.14, UTF-8 모드, workspace 의존성, selenium 설치, 허용된 별도 TEMP 경로, Python을 PATH에 추가하고 python -m pytest -q -ra --tb=no tests 실행 결과 **752 passed, 96 failed, 108 errors, 3 skipped, 2 warnings**. 따라서 전체 회귀는 **통과하지 않았다**. 대표 원인은 core.autocrlf=true checkout으로 Git blob fingerprint test가 LF 원본과 CRLF 작업 파일을 다르게 비교한 점, Windows sandbox가 symlink 생성/외부 임시 파일 조작을 막은 점, Windows에서 subprocess가 SQLite 파일을 열린 상태로 두어 정리 중 잠금이 발생한 점이다. 모든 실패를 개별 수정하거나 프로젝트 회귀로 판정한 것은 아니다. Linux CI가 이 코드의 전체 회귀를 검증해야 한다.
- 기준 커밋의 과거 940 PASS / 2 SKIP 및 GitHub Actions 39225637124 결과를 이번 코드의 새 결과로 재사용하지 않는다.
- 새 workflow는 수정했지만 push 제한으로 GitHub Actions를 새로 실행하지 않았다. 이 결과 문서의 Chromium PASS는 로컬 Windows에서 직접 실행한 결과다.

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
