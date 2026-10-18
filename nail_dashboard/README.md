# Nail Atlas — 독립 네일 트렌드 대시보드 MVP (B안)

**4개 화면이 전부 자체 SQLite DB → 저장소 어댑터 → Python 집계 → FastAPI → JS 화면 순서로 동작한다.** 기존 프로젝트의 `/shop`·`/jobs` 소스나 DB는 사용하거나 변경하지 않는다.

## 실행 환경

- Python 3.11 이상, FastAPI 0.128 계열, Uvicorn, pytest/httpx(검증용)
- 저장소 루트에서 실행하며 인터넷/API 키·n8n 계정·Docker·외부 DB 불필요

```powershell
python -m pip install -r requirements.txt
python -m nail_dashboard.db seed
python -m uvicorn nail_dashboard.app:app --host 127.0.0.1 --port 8010
```

이미 FastAPI 등이 설치된 환경에서 `requirements.txt` 설치를 생략할 수 있다. 최초 두 줄은 저장소 루트에서 실행한다. 예를 들어 브라우저에서 **http://127.0.0.1:8010/nails** 를 연다. JSON API 문서는 **http://127.0.0.1:8010/nails/api-docs**.

- `python -m nail_dashboard.db init` : 없는 DB/테이블만 생성, 기존 데이터 보존
- `python -m nail_dashboard.db seed` : 없는 데모 레코드를 입력. 기존 게시물이 있으면 **건너뜀**
- `python -m nail_dashboard.db seed --reset` : **위험! 기존 데모 DB 파일을 삭제하고 가상 데이터 208건으로 초기화하므로 반드시 백업 후 사용**
- DB 기본 위치: `nail_dashboard/data/nails.db` (`.gitignore` 대상)
- 별도 DB 사용: `NAIL_DB_PATH=/some/path/nails.db` 환경변수 (Windows PowerShell: `$env:NAIL_DB_PATH='C:\temp\nails.db'`)

## 주요 기능

대시보드: 전체/개별 브랜드 KPI(분석·수집·릴스·평균 반응), 13주 게시 빈도, 콘텐츠 형식별 평균, 시간대별 중앙값, 직접시술/시트형 도넛.

태그 분석: 전체 및 디자인·컬러·제품·시즌·콘텐츠 5분류, 데이터베이스 게시물-태그 관계 집계, 14건 단위 페이지. 오른쪽 브랜드 선택과 표의 전체 데이터 범위를 독립 취급.

브랜드 비교: 오른쪽 선택과 별개로 모든 브랜드의 반응 중앙값과 최근 4주 데모 지수 막대, 전체 표.

상위 게시물: 브랜드별 상위 20건, 반응 내림차순 15+5 페이지 이동, 브랜드 변경 시 페이지 1 초기화, 결측 조회수 및 성과지수 `—` 표시. 실제 인스타그램 콘텐츠·링크는 사용하지 않음.

저장된 보고서 조회: 버튼으로 SQLite의 최신 report_run 및 통계를 **재조회**. 외부 수집/갱신 자동화는 구현되지 않음.

## 명확한 데모 공식 / 미구현

- 반응 = 자체 샘플의 `likes + comments`.
- 릴스 비중 = 수집된 게시물 중 릴스 수 / 전체 수집 수 × 100, 반올림. **관찰값과 맞는 후보를 데모 규칙으로 채택했을 뿐 원본 소스의 공식은 미확인**.
- 브랜드 최근 4주 지수 = 최근 28일 반응 중앙값 / 전체 기간 반응 중앙값. 최근 3건 미만이면 결측. **독립 데모 공식**.
- 태그 수요지수 = 태그 게시물 반응 중앙값 / 전체 분석 게시물 반응 중앙값. 태그 표본 3건 미만 결측. **독립 데모 공식**.
- 태그 4주÷8주 = 최근 4주 주당 게시 수 / 이전 8주 주당 게시 수. 분모 0일 때 결측. **독립 데모 공식**.
- 게시물별 성과지수: **미구현(—)**. 원본 공식 추측/복제 금지.
- `수요 높음`은 데모 지수 1.25 이상, `수요 낮음`은 0.8 미만, 나머지는 보통. 원본 임계값 아님.

**미확인:** 원본 사이트의 브랜드-태그 상호작용의 모든 조합, 수집 API와 DB 구조, 계산식, 수요 편차, 시간대 경계, 링크 클릭 동작. 네 개 화면 중 관찰된 동작만 재구현함.

## 테스트

```powershell
python -m pytest -q nail_dashboard/tests/test_dashboard.py
python -m nail_dashboard.tests.live_http_smoke
node --check nail_dashboard/static/app.js
```

브라우저 자동화는 Playwright가 설치되고 브라우저가 허용되는 PC에서 다음을 별도로 실행한다. 로컬 서버가 열려 있어야 한다.

```powershell
python -m pip install playwright
python -m playwright install chromium
python -m nail_dashboard.tests.browser_e2e
```

테스트는 모두 `tempfile` 테스트 DB를 사용한다. 브라우저 테스트만 사용자가 켜둔 데모 DB를 읽는다. 원본 개발 DB는 수정하지 않는다.

## 한계와 연결 지점

- 샘플은 **가상 브랜드 4곳 및 가상 게시물 208건**으로 구성되며 정확한 숫자는 seed 이후 DB 데이터에 따라 바뀐다.
- 현재 DB는 데모 전용이며 로그인, 사용자별 비밀 데이터, 관리자 수정, n8n, Instagram API, 외부 호스팅, 실시간 수집, 실행 예약, 고성능 대규모 분석을 제공하지 않는다.
- 사용자 데이터 연동 상태는 **미연동**이다. `repository.py`를 사용자 DB/API 어댑터로 바꾸고 `metrics.py`의 집계 계약을 유지할 수 있다. 보고서 생성·데이터 검증·권한과 운영 보안 정책은 실제 연결 전에 별도 설계가 필요하다.
\n## Regression verification 2026-10-18 18:17 KST

Reproducible verification from repository root:
    python -m pytest -q nail_dashboard/tests/test_dashboard.py
    python -m nail_dashboard.tests.live_http_smoke

33/33 pytest PASS in the validation environment with Node.js installed. 15 original + 18 new parameterized cases cover SQLite-to-KPI/chart/brand/tag/posts correctness, 15/5 paging, JS brand change page reset, no data, zero denominators and NULL vs 0. The tests use isolated temporary SQLite files. Undefined ratios return API null and display '—' (not 0%). Chrome automated E2E remains unverified; see TEST-REPORT.md.

