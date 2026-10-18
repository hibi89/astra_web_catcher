> [!IMPORTANT]
> ## ASTRA 사용자 확정 설계 — 반드시 먼저 읽기 (2026-10-18)
> **최우선 원본:** [사용자 첨부 설계 3장 문자 전사](docs/ASTRA_CANONICAL_DESIGN_2026-10-18.md) → [원본 인수인계 TXT](docs/source/ASTRA_USER_HANDOFF_ORIGINAL_2026-10-18.txt) → [7단계 로드맵·68~118h 추정](docs/ASTRA_ROADMAP_AND_ESTIMATE_2026-10-18.md) → [다음 채팅 실행 가이드](docs/ASTRA_NEXT_CHAT_HANDOFF_2026-10-18.md).
>
> **목표:** 웹사이트 자동 복제가 아니라, 참고 URL+사용자 시연에서 기능/사용 흐름을 관찰하고 사용자 DB/API 구조에 매핑해 독립 웹앱을 생성·검증하는 반자동 개발 보조도구. OHORA CSV/Nail Atlas는 테스트 사례일 뿐. 원본 DB 무단 변경 금지. v1 지원: 목록·검색·필터·상세·CRUD·기본 집계. 원본 서버 비공개 코드 취득·접근 제한 우회 목적 아님.
>
> **현재 차이:** main은 최초 도서·채용 앱 코드이며, `nail_dashboard/`는 `research/jp-nail-dashboard-20261018`, `nail_practice/`는 `experiment/ohora-practice-20261018`에 있음. 실험 브랜치의 최신 실행 상태를 확인하고 검증된 작업만 이어갈 것. **범용 URL/시연→명세→코드→테스트 파이프라인은 아직 미구현.** 다음 우선순위는 원본 로드맵 Step 2~3 통합 정리와 Step 4-A/B.

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

## 2026-10-18 20:54 KST — p4 Step 2 observation contract / Step 4-A prerequisite (one unit)

1. **Goal/stack:** Human-supplied read-only UI evidence normalized with Python Pydantic 2 (already in requirements). Common ASTRA engine foundation; not an OHORA-specific dashboard.
2. **Completed:** New astra_contracts/observation.py models, CLI validate/schema; synthetic filter fixture, tests, docs/OBSERVATION_CONTRACT_V1.md. Compared JSON Schema-only vs Pydantic model; selected Pydantic to avoid duplicate validators.
3. **Validation:** Python 3.13.5 / Pydantic 2.13.5 / pytest 9: 19/19 PASS; fixture CLI 2 observations / 2 references PASS; JSON Schema export PASS; compileall PASS. Github source blob SHA checked against local git hash. Original app, research and experiment suites NOT rerun.
4. **Stop point:** Contract model only. Actual browser evidence collection, historic notes conversion, automatic functional spec, DB/API mapping, codegen and end-to-end are unfinished.
5. **Failure / recovery:** Initial strict Pydantic model rejected JSON enum/datetime strings (3 failed / 16 pass); removed inappropriate global strict option, second run 19/19. Existing browser policy failures were not retried.
6. **Repo/branch/paths:** hibi89/astra_web_catcher, feature/observation-contract-20261018 branched from main dc23ee604d02513c890615a3a98440c1ea8a5270. New astra_contracts/{__init__,observation}.py, fixtures/observation_brand_filter.json, tests/test_observation_contract.py and docs/OBSERVATION_CONTRACT_V1.md; commit SHA = feature branch HEAD for this update.
7. **Production:** not applicable. Read-only CLI: python -m astra_contracts.observation validate fixtures/observation_brand_filter.json .
8. **Data/backups/security:** existing shop/jobs, nail_dashboard, nail_practice and all databases unchanged. Fixture is synthetic and contains no real PII/API secrets; validator rejects common secret fields but not all possible sensitive prose.
9. **Next single work unit:** convert ONE existing Japanese nail observation to the standardized evidence record using only grounded evidence pointers and explicit unknown claims; only then begin automatic Step 4-B specification. No original-site scraping, database/schema changes or deployments without permission.
10. **Record time / verification:** 2026-10-18 20:54 KST; local independent unit tests; GitHub blob equality and feature branch commit readback required. Baseline main SHA dc23ee604d02513c890615a3a98440c1ea8a5270; documentation base blob HANDOFF 46ac526c4bc90c8f43fb61565186ba09230be0de.

## 2026-10-18 21:07 KST — Step 2 archived brand-filter observation conversion

1. **Goal/stack:** Convert one historical Japanese nail dashboard brand-filter comparison to the reusable Pydantic 2 observation JSON contract.
2. **Completed:** Added `archived_report` evidence type; `fixtures/jp_nail_brand_filter_observation_20261018.json` contains ALL/OHORA screen state and two unknown claims. `evidence/jp_nail_brand_filter_source_20261018.md` identifies the original report SHA and records missing original screenshots.
3. **Tests:** `python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py` = 27/27 PASS; CLI validate 3 observations and 1 evidence item PASS; compileall PASS. Prior original-app suites and live browser not rerun.
4. **Stop point:** One archived record standardized. Automated observation capture and Step 4-B/4-C/4-D pipeline are not complete.
5. **Failure:** pytest invoked from outside the repo root gave import errors; corrected by running at repo root. No repeated blocked-browser attempt.
6. **Source/version:** `hibi89/astra_web_catcher` / `feature/observation-contract-20261018`; code change commit `88d65e1d4056efe50d429e524f673a44a380cb01`. Original source report blob `b9d676e0e7ba8af2124a0785e8c57b9ab6195f1b`; main unchanged.
7. **Deployment:** Not applicable; read-only local CLI, Python 3.13 / Pydantic 2.
8. **Protection:** No source-site API/cookie acquisition or live DB writes. Research source, user data, original apps preserved. The archival document is secondary evidence, not retrieved screenshot files.
9. **Next ㄱ:** Step 4-B small functional specification JSON derivation from evidence, with unknowns and approval gates preserved; do not infer original backend or alter DB/API.
10. **Recorded/verified:** 2026-10-18 21:07 KST, local 27 PASS, GitHub source/fixture/test/doc blob hashes compared with locally tested files; branch/BOOK readback pending.
