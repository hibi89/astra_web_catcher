# STATUS — Astra Web Catcher

**Updated 2026-10-18 16:17 KST**. Repository target `hibi89/astra_web_catcher` / `main` was empty at task start. Tested source developed locally under `/mnt/data/astra_web_catcher` and **22 files committed to GitHub**. Verified source commit: `62eaab17b6ee11b4a27cd7caec2fce752b8815ab`. A later documentation-only commit may advance HEAD.

## Completed locally

- One FastAPI server, two original frontends: `/shop` (BookHarbor), `/jobs` (CareerWay).
- 2 demo users; salted password hashes, 12h HttpOnly SameSite=Lax sessions; sessions determine user identity.
- 13 passing pytest tests on independently seeded temporary SQLite DBs.
- Real Uvicorn HTTP test including stop/restart and persistent cart/bookmark, test order + private API authentication PASS.
- 24 fictional books, 5 categories, 7 companies, 26 fake jobs; SQLite initial migration and idempotent seed.
- Stock-safe transactional orders with snapshots, unique request keys, parallel conflict tests; job filter, bookmark, apply, duplicate/closed guards.
- README, architecture, test report, reviewer pack, AGENTS/REQUIREMENTS, browser smoke script.
- `node --check app/static/app.js` PASS; `python -m compileall -q app tests` PASS.

## Pending / blocked

- Browser E2E and screenshots: attempted Chromium; `net::ERR_BLOCKED_BY_ADMINISTRATOR` navigating localhost. The script is available for use on another host. UI operation unverified.
- Next.js/Prisma/TypeScript original preferred tech: replaced after npm registry DNS `EAI_AGAIN` and use of available Python packages. TypeScript typecheck and Next.js production build not applicable.
- GitHub source commit `62eaab17b6ee11b4a27cd7caec2fce752b8815ab` verified with `app/main.py` and `README.md` re-fetch (22 files). No Vercel deployment requested; deployment not applicable.
- Public Wanted reference page couldn't be read; its behavior was independently designed from spec. YES24 public nav/search/cart/order links were read, no transactional operations attempted.

## Next steps

1. Re-fetch GitHub `main` HEAD and compare source and handoff document versions; initial source commit is already verified.
2. On user's localhost, install requirements, seed, start, open `/shop` and `/jobs`, inspect browser Console/Network; run `python tests/browser_smoke.py` and collect screenshots.
3. If discrepancies in reference behavior matter, request narrowly scoped user recording of search/filter/cart/order and bookmark/apply flows; no secrets/traces.
4. Update reports and resolve any actual front-end failures, then re-test; do not claim success without browser evidence.

## 2026-10-18 16:35 KST — 검증 완료 업데이트

- 사용자 직접 검증 보고: 두 앱의 주문·지원 및 새로고침 후 데이터 유지 성공. ChatGPT 브라우저 직접 검증은 기존 정책 차단으로 계속 미검증.
- 새로 실행: `python -m pytest -q tests/test_mvp.py` **13/13 PASS**, `python tests/live_http_smoke.py` **PASS**, `python tests/live_integrity_check.py` **6/6 PASS** (실제 HTTP 서버·동시 요청·독립 temp SQLite DB).
- 결과: 서버 재시작 후 A/B 세션·카트·관심·지원 영속성; 소유권 404; 서버 총액 18,000원·재고 -2·주문 스냅샷; 재고 1개 동시 주문 201/409; 중복 지원 동시 201/409·DB 1행; 주문 키 재전송 중복 방지.
- 앱 소스 변경 없음. 재현용 `tests/live_integrity_check.py` 추가, 커밋 `9d2ce31aa353bcdbd53b3bcca815a5b87c372645`. TEST-REPORT 및 REVIEW-PACK 갱신.
- **다음:** 실제 사용자 PC의 브라우저 Console/Network 검사나 문제 발견 때만 수정. 원래 요청 기술 스택과 다른 FastAPI 구현 유지 여부는 사용자 검수 결정에 따름.

## 2026-10-18 — 사용자 확정 설계 및 p4 다음 채팅 복원 기준 (문서 작업만)

- 사용자 첨부 원설계 3장 원문 전사: `docs/ASTRA_CANONICAL_DESIGN_2026-10-18.md`. 업로드된 원본 TXT 원문: `docs/source/ASTRA_USER_HANDOFF_ORIGINAL_2026-10-18.txt`. 분석·제안 문서: `docs/ASTRA_ROADMAP_AND_ESTIMATE_2026-10-18.md`; 단축 재개: `docs/ASTRA_NEXT_CHAT_HANDOFF_2026-10-18.md`.
- **ASTRA 실제 목표:** 참고 URL+사용자 시연에서 기능·사용 흐름을 배우고, **사용자 DB/API를 존중하여** 필요한 부분을 승인 후 매핑·개선해 독립 웹앱을 생성·테스트하는 범용 반자동 개발 보조도구. 오호라 CSV·네일 대시보드는 **검증 사례**이지 최종 서비스 목표가 아님.
- 원설계 7단계: (1) 명세 기반 앱 생성 검증 (2) 원본 관찰 (3) 관찰 기반 재구현 (4) URL/시연→명세→코드→테스트 연결 (5) 새로운 사이트 2~3개 재사용 검증 (6) 기존 현업 프로젝트 통합 (7) 허가된 저위험 프로젝트 제한적 실사용.
- 최신 사례 검증: `/shop`, `/jobs` 13/13+HTTP 6/6; 연구 브랜치 `nail_dashboard/` 33/33+Windows Playwright E2E PASS; 실험 브랜치 `nail_practice/` 16/16+CSV 294계정/1845게시물/5953미디어 및 사용자의 첫 화면 렌더 성공. 단, 실험판 전체 브라우저 테스트는 미검증.
- **가장 중요한 미완료:** 범용 URL·시연→관찰 명세→사용자 DB/API 매핑→코드 생성→자동 테스트를 잇는 파이프라인. 이 부분을 기존 앱 제작과 혼동하지 말 것.
- 보조 AI 공수 추정은 공식 검증치가 아닌 약 **20% 진행/68~118시간 잔여(중심 90h)**. 실제 완료를 보장하지 않음.
- 이번 반영은 **문서 및 인수인계만**. main 애플리케이션 코드·DB·기존 테스트 변경 없음. 실험과 연구 브랜치의 소스/데이터/동결 스냅샷 보존.
- 다음 채팅은 `HANDOFF.md` 최상단의 확정 설계 링크를 최우선으로 읽은 뒤 **Step 2~3 표준화 및 Step 4-A/B 공통 엔진 제작**부터 진행.

## 2026-10-18 20:54 KST — p4 Step 2/4-A observation evidence contract (isolated)

- Branch: feature/observation-contract-20261018, forked from main dc23ee604d02513c890615a3a98440c1ea8a5270. Source, fixture, 19 tests and explanation added. No modifications to existing app and DB; no merge to main; production not deployed.
- Implemented evidence-kind IDs, provenance certainty observed/inferred/unknown, UI state before/after, feature enum, link integrity, timezone-annotated timestamps, simple secret/path filtering, CLI validate + JSON Schema export.
- Local verification: 19/19 pytest PASS, sample CLI 2 observations PASS, JSON Schema export PASS, compileall PASS, new source blob hash matches the tested file. Entire baseline app test suite and physical browser tests not rerun.
- **Outstanding:** real observation records, Step 4-B function specification / DB mapping, code generation, live browser/API verification. JSON Schema export does not enforce Pydantic cross-record rules; use CLI validate.
- **Next ㄱ (one unit):** safely transform one existing documented brand-filter observation into a versioned JSON record with original evidence distinctions, then test readback. The research docs remain the historical source of truth.

## 2026-10-18 21:07 KST — p4 archived brand-filter case completed

- On feature branch, converted **one** historical ALL→OHORA state comparison into `fixtures/jp_nail_brand_filter_observation_20261018.json` with a provenance manifest and new `archived_report` evidence type.
- Source: research branch `research/jp-nail-dashboard-20261018`, blob `b9d676e0e7ba8af2124a0785e8c57b9ab6195f1b`. Original screenshots were not obtained in this run; no click trace, live API/n8n source or original formulas verified.
- **Local:** 27/27 contract and conversion tests PASS, CLI 3 observations/1 evidence PASS, compileall PASS. An initial invocation from wrong CWD failed imports; corrected repo-root run passed. Previous app suites/live browser not rerun.
- **Preserved:** main, shop/jobs, research/experimental apps and databases untouched. Not deployed.
- **Next ㄱ:** Step 4-B reusable evidence-to-functional-spec JSON transformation, keeping unknown claims and approval boundaries explicit. This step was **not** implemented here.

## 2026-10-18 21:18 KST — p4 Step 4-B draft functional spec generator

- New `astra_contracts/functional_spec.py` transforms validated observation bundles into deterministic, **unapproved** functional-spec JSON to stdout. Source SHA-256 fingerprint, observed-only candidate features, evidence quality, actual changed fields, inferred/unknown list, and pending approval gates. Generic search scenario tested; no UI-specific nails hardcoding.
- **Verified locally:** 46/46 pytest PASS (27 prior + 19 new), CLI JSON parse PASS, golden output identical, compileall PASS, new GitHub source/test/fixture/doc blob SHA matches locally tested files. `fixtures/jp_nail_functional_spec_draft_20261018.json`: candidate 1, unresolved 2, pending gates 4.
- **Preserved:** main `dc23ee604d02513c890615a3a98440c1ea8a5270`, app, research, experiment branches, data unchanged. Production/Vercel not applicable. Browser tests/API tests not rerun; no backend or DB inferred.
- New code commit `bcfd140597e5ba750bd8586cf898a317bd7eb0d4`, branch `feature/observation-contract-20261018`; documentation commit and branch readback follow.
- **Next ㄱ:** separate owned DB/API mapping contract & mismatch report, no mutations or approval bypass.

## 2026-10-18 21:31 KST — p4 Step 4-B owned-schema mapping diagnostics (one unit)

- **Added:** `astra_contracts/data_mapping.py`, `tests/test_data_mapping.py`, synthetic schema/report JSON and `docs/DATA_MAPPING_CONTRACT_V01.md` on `feature/observation-contract-20261018`. Code commit `6623cb139acd133b3cc89346f3b4a1f6d90a9e56`.
- **Capability:** offline explicit UI-field→declared DB/API resource-field mapping comparison; classify unbound, absent resource/field, wrong scalar type, nullable mismatch and unknown types. Compatible means structural only, NOT approved. Report retains old unresolved assumptions and approval gates. Example synthetic 10 fields: 3 structural, 4 unbound, 1 missing resource, 1 missing field, 1 type mismatch. User schema was not supplied; no live verification.
- **Tests:** 71/71 PASS (previous 46 + new 25); Python compileall PASS, CLI JSON output PASS; hashes of 5 new Git blobs match locally tested files. First 1 failing test was stale mapping in empty-candidate test, corrected fixture and all passed. No existing application/browser/live API suite rerun.
- **Security/preservation:** never connect/modify actual API, DB, credentials, code or schema; fictional test manifest explicitly synthetic; `main`, shop/jobs, independent nail dashboard/experiment, data unchanged. No Vercel deployment.
- **Next `ㄱ`:** isolated independent code-generation contract with explicit safety/approval boundaries (not actual generation or live deployment). Need user authorization and owned schema before connecting to real client DB.
