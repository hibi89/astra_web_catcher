# Astra Web Catcher — 독립 로컬 MVP 2종

가상의 **북하버**(도서 쇼핑몰, `/shop`) 및 **커리어웨이**(채용 서비스, `/jobs`)를 한 로컬 서버에서 실행하는 실습 프로젝트입니다. YES24·원티드는 공개 서비스 흐름 참고 대상으로만 사용했습니다. 실제 업체·상품·채용 공고·주문·지원 데이터를 사용하거나 외부 서비스로 전송하지 않습니다.

## 기술 선택과 환경 제약

원안은 Next.js + TypeScript + Prisma + SQLite였으나, 검증 환경의 npm 패키지 레지스트리 DNS가 `EAI_AGAIN`으로 차단되고 빈 GitHub 저장소에 기존 소스가 없었습니다. 그래서 **이미 설치된 FastAPI 0.128 / Python 3.13 / SQLite / vanilla JavaScript**를 이용했습니다. 단일 프로세스, 별도 프론트엔드 번들 단계 없음, 각 API에 SQL DB 직접 연결이라는 장점이 있습니다. **이 결과물을 Next.js/Prisma/TypeScript 구현으로 부르면 안 됩니다.** TypeScript 검사와 Next.js production build는 이 스택에 해당하지 않습니다. Python 컴파일·JS 구문 검사·ASGI 구동으로 대체 검증했습니다.

## 설치 / 초기화 / 실행

요구사항: Python 3.11+ (검증: Python 3.13), 로컬 포트 8000, SQLite (Python 내장), npm 불필요. 프로젝트 루트에서:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.db init
python -m app.db seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`init`은 **기존 데이터 보존**하며 스키마를 생성하고, `seed`는 DB에 사용자가 이미 있을 경우 전체 샘플을 중복 생성하지 않습니다. 실행에 필요한 네트워크는 첫 `pip install`뿐입니다. 검증 환경에는 필요한 패키지가 설치되어 있었습니다.

실행 후:

- 시작: <http://127.0.0.1:8000/>
- 도서 목록: <http://127.0.0.1:8000/shop>
- 장바구니: <http://127.0.0.1:8000/shop/cart>
- 주문 내역: <http://127.0.0.1:8000/shop/orders>
- 채용 목록: <http://127.0.0.1:8000/jobs>
- 채용 마이페이지: <http://127.0.0.1:8000/jobs/me>
- API 명세(OpenAPI): <http://127.0.0.1:8000/docs>

### 테스트 계정 (로컬 데모 전용)

| 사용자 | 아이디 | 비밀번호 |
| --- | --- | --- |
| A | `demo_a` | `DemoPass!2026` |
| B | `demo_b` | `DemoPass!2026` |

기본 비밀번호는 실사용을 위한 것이 아닙니다. DB에는 PBKDF2-SHA256 salt 기반 해시만 저장합니다. 인증 쿠키는 HttpOnly/SameSite=Lax, HTTPS 구동 시 `ASTRA_SECURE_COOKIE=1`로 Secure 활성화하세요. 외부에 서비스를 노출하지 마세요.

### 테스트 · 정적 분석

```bash
python -m pytest -q
node --check app/static/app.js      # Node 설치 시에만
python -m compileall -q app tests
python tests/live_http_smoke.py  # 별도 Uvicorn 프로세스 2회로 재시작/영속성 검증
python tests/browser_smoke.py        # Playwright 설치 + 로컬 Chromium 필요
```

테스트는 `tmp_path` 하위 **별도 SQLite DB**를 생성하며 개발 DB의 데이터를 변경하지 않습니다. 브라우저 스모크 테스트도 별도 임시 DB를 사용하도록 작성했습니다. **2026-10-18 검증 환경에서는 Chromium 로컬 HTTP 탐색이 `ERR_BLOCKED_BY_ADMINISTRATOR`로 차단되어 브라우저 시연을 완료하지 못했습니다.** 테스트는 미실행/환경 차단으로 기록하고 통과 처리하지 않았습니다. 로컬 PC에서는 `playwright install chromium` 후 `python tests/browser_smoke.py`를 실행할 수 있습니다. 스모크 스크립트는 `CHROME_EXECUTABLE` 환경변수 또는 PATH의 `chromium`/`google-chrome`을 우선하며, 없으면 Playwright 설치 Chromium을 사용합니다. Windows에서는 `playwright install chromium` 후 실행할 수 있습니다.

### 데이터 및 초기화 경고

기본 DB는 `data/app.db`이고 `ASTRA_DB_PATH`로 변경할 수 있습니다. DB 파일은 `.gitignore`로 제외합니다.

**경고: 다음 명령은 선택한 DB와 사용자의 모든 장바구니·주문·관심·지원 내역을 영구 삭제합니다. 실행 전 백업하세요.**

```bash
# Linux/macOS
ASTRA_ALLOW_RESET=YES python -m app.db reset
python -m app.db seed

# Windows PowerShell
$env:ASTRA_ALLOW_RESET='YES'; python -m app.db reset
python -m app.db seed
```

개발 DB 초기화를 원하지 않으면 `reset`을 실행하지 마세요. SQLite 파일을 백업하려면 서버를 종료하고 `data/app.db`를 복사하세요. WAL 모드의 실행 중 백업은 SQLite 온라인 백업 기능을 사용하세요.

## 구현 범위 및 의도적 제외

도서: DB 조회·검색/카테고리·정렬·페이지·상세·장바구니 합산/수정/삭제·트랜잭션 주문/재고·idempotency·가격 스냅샷·본인 주문 상세. 채용: DB 조회·키워드/직무/지역/경력/진행 상태 복합 필터·상세·관심 등록/해제·메모 지원·중복 방지·마이페이지/본인 상세. 비회원은 읽기 전용 공개 목록/상세만 허용합니다.

**의도적으로 제외:** 회원가입, 실제 결제·배송, 실제 회사 계정, 파일 업로드, 이메일 발송, 비밀번호 복구, 운영 환경 배포, 관리자. UI·데이터는 자체 제작 샘플입니다. 실제 YES24/원티드의 정책이나 백엔드 구현과 같다는 의미가 아닙니다.

## 검증 및 설계 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md): DB 관계·API·접근 제어·트랜잭션
- [`TEST-REPORT.md`](TEST-REPORT.md): 실제 테스트 로그·미검증 항목
- [`REVIEW-PACK.md`](REVIEW-PACK.md): 독립 리뷰어 전달 자료
- [`HANDOFF.md`](HANDOFF.md), [`STATUS.md`](STATUS.md): 다음 채팅 인수인계

## 추가 HTTP 무결성 회귀 테스트 (2026-10-18)

개발 DB(`data/app.db`)를 변경하지 않고, 임시 DB와 실제 Uvicorn 서버 프로세스를 사용하여 다음 검증을 실행할 수 있습니다.

```bash
python -m pytest -q tests/test_mvp.py
python tests/live_http_smoke.py
python tests/live_integrity_check.py
```

`live_integrity_check.py`는 서버 종료·재시작 시 세션·장바구니·관심·지원 데이터 유지, A/B 소유권, 금액/재고/기존 주문 가격, 재고 1개 병렬 주문, 병렬 중복 지원을 검증합니다. 2026-10-18 재검증: pytest **13/13 PASS**, HTTP 재시작 **PASS**, HTTP 무결성 **6/6 PASS**. 브라우저 자동 E2E는 환경 차단으로 미검증이며, 사용자는 별도 로컬 브라우저로 기본 UI 흐름 성공을 보고했습니다.

## p4 공개 Selenium 실제 브라우저 검증 경로 (2026-10-19)

참고 사이트 관찰 기능을 **기존 사용자 데이터나 main을 변경하지 않고** 검증하기 위한 선택적 공개 테스트 절차입니다. 일반 실행은 네트워크·Chrome·파일 생성이 없는 dry-run입니다.

```sh
python -m scripts.public_capture_live_check          # 안전한 준비 상태만 출력
python -m pip install selenium                       # 실제 실행 가능한 환경에서만
python -m scripts.public_capture_live_check --run    # 허가된 Selenium 공개 폼 1회 조작→전후 증거→기존 intake 검증
```

GitHub의 [p4 공개 폼 브라우저 워크플](.github/workflows/p4-public-live-browser.yml)은 해당 기능 브랜치만 대상으로 GitHub Actions Chrome/Xvfb를 통해 동일한 공개 테스트를 시도합니다. 성공 시 익명화된 증거를 단기 보관할 수 있습니다. **이 README 기준 실제 원격 워크플 성공 여부는 미확인**이며, 로컬 **74/74 선택적 자동 테스트만 통과**했습니다. 운영 권한·원본 사이트 기능의 독립 승인·실제 고객 DB/API 연동·배포가 완료됐다는 의미는 아닙니다.

세부 한계와 재현 절차: [PUBLIC_SELENIUM_LIVE_RUNNER_20261019.md](docs/PUBLIC_SELENIUM_LIVE_RUNNER_20261019.md).


## p4 합성 시계열 Chart/Table 미리보기 (2026-10-19)

**실제 클릭 가능한 오프라인 HTML 시제품**을 기존 고객 DB와 무관한 합성 데이터로 생성합니다. 원본 사이트의 데이터/계산식/구현을 복제하지 않습니다.

    python -m astra_contracts.synthetic_chart_table_preview --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --output preview.html

원본 OWID 관측 증거를 파일 단위로 확인하려면 선택적으로 --archive /path/to/p4-owid-evidence.zip 을 추가합니다. 실측·실제 고객 데이터 사용이 아니라 **15건의 임의 수치**입니다. 관련 신규 테스트 포함 로컬 선택적 회귀 50/50 PASS와 Chromium Chart→Table→Chart 클릭 검증을 수행했습니다. 다만 전체 저장소 CI, Windows Edge, 고객 API/DB, 실제 배포 검증은 **미실행**이며, GenerationContract는 blocked_pending_review입니다.

전체 설명과 한계: [SYNTHETIC_CHART_TABLE_PREVIEW_20261019.md](docs/SYNTHETIC_CHART_TABLE_PREVIEW_20261019.md).

### Synthetic Chart/Table browser regression (offline)

Five-viewport Chromium + keyboard/XSS smoke (requires Playwright and installed Chromium): `python -m scripts.p4_synthetic_preview_browser_smoke --chromium /usr/bin/chromium --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json --archive /path/to/p4-owid-evidence.zip`. Latest local result: 50/50 selected pytest, 5/5 Chromium viewports, 1/1 HTML injection payload. No Windows Edge/Firefox/WebKit or full-repo claim; synthetic-only, all approval gates false. Full details: docs/SYNTHETIC_CHART_TABLE_PREVIEW_20261019.md.

### p4 Full regression and cross-engine browser evidence — 2026-10-19

On GitHub Actions [run 39220632083](https://github.com/hibi89/astra_web_catcher/actions/runs/39220632083), feature-branch full Python regression **894 passed, 2 skipped (historic OWID ZIP unavailable in CI), 0 failed**. Real Linux Chromium/Firefox/WebKit preview smoke **12/12 PASS**, real Windows Microsoft Edge **4/4 PASS** at desktop/mobile/small-mobile viewports (Chart↔Table, keyboard, HTML injection, 0 network/JS error). Reusable `scripts/p4_multi_browser_smoke.py` supports optional `--archive`; omitting it explicitly does **not** verify provenance. See `docs/P4_FULL_REGRESSION_CROSS_ENGINE_20261019.md` for command, versions, artifacts, skips and limits. All preview data synthetic, customer DB and generation/deployment still blocked.


### p4 synthetic SQLite API ↔ Chart/Table browser demo (2026-10-19)

An **isolated, in-memory SQLite** fixture now feeds a read-only FastAPI GET /api/demo/series and a GET /preview page. The page renders the existing original synthetic chart/table view from SQL results, then fetches the local API and compares a SHA-256 snapshot fingerprint. It flags a mismatch rather than falsely claiming live-data equality. No customer DB, credentials, persistent storage, main merge or production deployment.

Verified in [GitHub Actions run 39222673267](https://github.com/hibi89/astra_web_catcher/actions/runs/39222673267): **13/13 new API/DB tests PASS**, actual loopback HTTP Chromium E2E **PASS** including API GET, Chart/Table click/keyboard, DB-value change reflected after refresh, forged API SHA rejected; 0 requests to external origins and 0 JavaScript errors. This is not real customer integration or verified source semantics.

To reproduce from repo root:

    python -m pip install -r requirements.txt
    python -m pytest -q tests/test_synthetic_sqlite_dashboard.py
    python -m playwright install --with-deps chromium
    python -m scripts.p4_synthetic_sqlite_browser_smoke --fixture examples/p4_chart_table_synthetic_schema.json --rows examples/p4_chart_table_synthetic_rows.json

See docs/P4_SYNTHETIC_SQLITE_API_E2E_20261019.md for implementation, test logs, limitations and security/authorization boundaries.

### p4 Two-owner synthetic schema isolation (2026-10-19)

New disposable owner-shaped test fixture and **shared** SQLite `:memory:` demonstration: `astra_contracts/synthetic_owner_isolation.py` and `examples/p4_owner_demo_{schema,rows}.json`. Four explicit chart/table roles plus one explicitly declared owner key; all mappings **structurally compatible but unapproved**. Separate opaque HttpOnly cookies issued **only by the in-process test harness**, owner-predicated SQLite queries, read-only `GET /api/demo/series`, `GET /api/demo/owners/{owner}/series` (404 cross-owner), and `GET /preview`. No login, session issue or write API routes exposed. GitHub Actions [run #39225637124](https://github.com/hibi89/astra_web_catcher/actions/runs/39225637124): **full pytest 940 passed / 2 existing OWID evidence ZIP skips**, zero failures; **33/33 new isolation tests PASS**; real Chromium HTTP/SQLite/browser E2E **PASS**. Detailed limits, proof, commands and security scope: `docs/P4_SYNTHETIC_OWNER_ISOLATION_20261019.md`. This is not production authentication nor any real customer data access, generation or deployment.
