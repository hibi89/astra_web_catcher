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

## 2026-10-18 21:45 KST — Step 4-C safety preflight contract

- **Implemented** `astra_contracts/generation_contract.py`, `tests/test_generation_contract.py`, `fixtures/synthetic_generation_request_20261018.json`, `fixtures/synthetic_generation_contract_20261018.json`, `docs/GENERATION_CONTRACT_V01.md`; source commit `3e585b8f709d638f03942bbde1424aa2b15af6fb`.
- Verifies observation spec, synthetic owned-schema manifest, recomputed mapping report and restricted output request; blocks mismatched hashes/report edits, path escape, forged approval, incompatible or unknown fields. JSON only; **code_generated/files_written/approval/deploy/mutation all false**.
- **Tests:** 111/111 local pytest PASS, CLI golden match, compileall PASS, five Git blobs match local tested files. Sample: eight blockers, seven prior gates, four future review requirements.
- No original DB/API, external services, /shop, /jobs, research/practice apps, main or production modified. **No executable code generator or deployment completed.**
- **Next ㄱ:** separate isolated synthetic artifact-generation prototype or human review workflow, with safety separation maintained.

## 2026-10-18 KST — p4 Step 4-C runnable synthetic app generator

- Added `astra_contracts/synthetic_generator.py`, `tests/test_synthetic_generator.py`, `fixtures/synthetic_demo_catalog_20261018.json`, `docs/SYNTHETIC_GENERATOR_V01.md`; source commit `6151b15c4392400ce45d9113accc576bdd5ef109`, branch `feature/observation-contract-20261018`.
- **Actual files generated:** 7-file FastAPI/SQLite/HTML demo in a new empty temporary directory. GET list/category filter/search/detail/health and local SQLite persistence implemented only for fictional explicit data, not the original site. Downloadable ZIP built separately. Existing fail-closed GenerationContract is not bypassed.
- **Local evidence:** 134/134 regression tests PASS (prior 111 plus 23), generated app self-test PASS, independent fictional jobs sample PASS, compileall PASS. Uvicorn local HTTP 200 on /, /health, /api/items, category/search/detail, 404 on missing id; SQLite persistence checked. No manual GUI/Playwright browser validation or production deployment. Fixed first generated-template quote syntax error before final tests.
- **Preservation:** No writes to customer DB, external API, main, /shop, /jobs or nail research/practice. Only existing empty `astra-synth-*` folders directly under system temp allowed. No Vercel production.
- **Next ㄱ:** One isolated evidence/spec-to-synthetic-test bridge or stronger generator runtime validation, preserving explicit human approvals; generic automatic reference URL→app production system remains incomplete.

## 2026-10-18 KST — p4 Step 4-C spec-to-synthetic preview bridge complete

- Implemented `astra_contracts/synthetic_bridge.py` and 18 tests, docs. Source commit `381475b99d8246aff66cce9e6884c7b365c352c0` on `feature/observation-contract-20261018`.
- Validates the spec, synthetic declared schema, recomputed mapping report and matching **blocked** GenerationContract, generates 7-file independent fictional demo + `data/astra_preview_trace.json`. Candidate feature category tests only; original claims, raw data and formulas are not code. Current sample: 1 synthetic filter route, 2 unknown issues, 7 mapping mismatches, not approved.
- **Local evidence:** full focused regression **152/152 PASS** (134 prior+18 new), compileall PASS, generated demo self-test PASS; Uvicorn localhost HTTP 200 for root/health/list/filter/search/detail and 404 unknown item. One overly broad source-code grep test was corrected before final pass. Original app or browser Playwright suite not rerun.
- No original website connection, customer DB access, changes to main/shop/jobs/nail research/practice, permissions/credential alterations, or deployment. Earlier fail-closed production-code preflight retained.
- User-facing preview ZIP `astra_bridge_preview_20261018.zip`; next `ㄱ` should implement one reviewed synthetic acceptance assertion / actual browser smoke step rather than claim production readiness.

## 2026-10-18 22:28 KST — p4 synthetic generated-app acceptance (one unit)

- Added `astra_contracts/synthetic_acceptance.py`, `tests/test_synthetic_acceptance.py`, `docs/SYNTHETIC_ACCEPTANCE_V01.md`; updated `astra_contracts/synthetic_bridge.py` and existing test. Previously placeholder `category=sample` returned no synthetic records; trace URLs now use percent-encoded **actual fictional fixture values**. Code commit `3d5065ef937da35d0be03d626df1a1972499d02b`.
- **Validation:** 170/170 pytest PASS (previous 152 + new 18), compileall PASS, 8 generated synthetic files, 12 acceptance checks PASS, separate fictional jobs fixture PASS. Actual Uvicorn loopback HTTP 200 root/health/list/Korean category filter/search/detail, 404 missing detail and 422 invalid limit. TestClient also checks exact rows, escaping, SQL persistence and template/trace tampering.
- **Boundaries:** Existing production-code `GenerationContract` remains `blocked_pending_review`. No customer DB/API, original website, deployment or source-app changes. The report explicitly marks `original_behavior_verified=false`, `production_ready=false`. GUI browser/Playwright E2E not run.
- Baseline `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged; work on `feature/observation-contract-20261018`. **Next ㄱ:** reviewer decision record for evidence/field semantics, or a supported actual browser UI E2E; any real data integration requires explicit approval.

## 2026-10-18 22:39 KST — p4 evidence/field semantic review record implemented

- **One unit completed:** new `astra_contracts/reviewer_decisions.py`, 23 new tests, 13-item synthetic/archived review packet, `docs/REVIEW_DECISION_RECORD_V01.md`. Source commit `39171ff46d389f87a926db06f5e93963c0c73816`, isolated branch `feature/observation-contract-20261018`.
- **Behavior:** deterministic source fingerprints; 1 archived observed claim, 2 unresolved behaviors, 10 field mapping review items. Optional user-authored opinions with rationale, exact packet SHA, no stale input, no unsupported marks for archival or incompatible fields. No review decision written or attributed to the user.
- **Validation:** full focused pytest **193/193 PASS** (170 existing + 23 new); Python compileall PASS; CLI JSON generated and validated, 13 items. Four Git source/test/fixture/document blob SHA checks matched local test files.
- **Critical:** Record claims remain unverified; `reviewer_identity_verified`, `field_meanings_verified`, `user_approval_verified`, `database_access_authorized`, `code_generation_authorized`, `deployment_authorized` and all other permission flags stay **false**. Existing `GenerationContract` keeps `blocked_pending_review`. No real source, client DB/API or actual browser E2E, no deployment.
- **Preserved:** existing main/shop/jobs, nail research/experiment and databases untouched. **Next `ㄱ`:** isolated manual-review UX or reviewed packet import/export safety; user real consent separate.

## 2026-10-18 KST — p4 isolated local review UI complete

- Added `astra_contracts/review_ui.py`, `review_ui.html`, `review_ui.css`, `review_ui.js`, `tests/test_review_ui.py`, `docs/REVIEW_UI_V01.md`; source commit `57c29202e617cf1308af3a9feb0d9676c53203dc` on `feature/observation-contract-20261018`.
- Capability: display 13 archived/synthetic review items with grouping and per-item opinion/rationale; filter preserves drafts; validate and save **unauthenticated, unapproved opinion** in an isolated temporary JSON file, then reload. Existing `record_opinions` validation rejects unsupported proposals on unknown/archived/incompatible items. All authorization flags false.
- **Verified:** all 10 suites **213/213 PASS** (193 prior + 20 new), Python compileall PASS, Node JS syntax PASS; real localhost Uvicorn GET HTML/JS/CSS/packet and POST+GET temporary opinion HTTP 200. No actual user opinion attributed.
- **Limit:** Playwright Chromium localhost navigation refused with `net::ERR_BLOCKED_BY_ADMINISTRATOR`; GUI browser E2E **not verified**. No original URL/DB/API access, migration, real codegen, deployment. Existing `main` and /shop, /jobs, nail research/practice untouched.
- **Next `ㄱ`:** manual/eligible-browser UI acceptance or reviewed opinion import/export with provenance and no authorizations. Current `GenerationContract` still blocks implementation.

## 2026-10-18 KST — p4 review opinion JSON transfer

- **One-unit feature:** `review_transfer.py` with an explicit no-authorization ReviewTransferBundle, deterministic packet/record fingerprints and reconstruction of the current `record_opinions()` against exact review items; localhost GET `/api/export/{id}`, POST `/api/import`, download/import buttons. Source commit `293d8f661642ab3e3cfc4d20546b9bd5013947b2`; feature branch only.
- **Tests:** all 11 focused suites **237/237 PASS** (prior 213 + new 24); compileall and JS check PASS, real localhost Uvicorn save/export/import/readback HTTP 200. Six new/changed source, tests, doc Git blob SHAs match tested local bytes.
- **Security:** stale packet and corrupt/forged record rejection, 64 KiB cap, local ephemeral token, host/origin safeguards, exclusive temporary JSON storage. SHA is NOT authenticated identity or consent; approval/codegen/database/deploy flags remain false. No original site, customer DB/API, original app or production activity; browser GUI click E2E still unverified due earlier administrator block.
- **Next `ㄱ`:** human browser acceptance if eligible or authorized original evidence reconfirmation; no repeat of blocked Playwright in this environment. `main` still `dc23ee604d02513c890615a3a98440c1ea8a5270`.

## 2026-10-18 KST — p4 local evidence-file inventory and hash verification

- **New one-unit feature:** `astra_contracts/evidence_integrity.py`, tests, docs, archived-case snapshot JSON. Source commit `206b2eafb2b51679651819a05e0356dc71ba26d9` on `feature/observation-contract-20261018`.
- Produces untrusted local evidence manifest and offline file-size/SHA-256 check tied to a strict observation-bundle digest; flags absent, modified or unsafe files, rejects symlinks/unsafe paths, caps 10MiB, checks evidence kind/extension, basic signature/credential patterns. Does not fetch URLs, generate code, change observed claims or authorize source use.
- **Evidence:** all focused local suites `python -m pytest -q tests/test_*.py` **270/270 PASS** (237 prior plus 33 new), `compileall` PASS, CLI snapshot/verify PASS, four remote Git blobs exactly match locally tested source/test/doc/fixture hashes. One preexisting httpx warning.
- **Historical example:** only the **secondary archived report** file passes byte-level verification. Not a real browser screenshot or captured click trace; site behavior, formulas, actual capture authenticity, reviewer consent all remain unverified and approval flags false.
- **Preserved:** user data and DB/API, shop/jobs, independent research branches, main `dc23ee604d02513c890615a3a98440c1ea8a5270`, deployments. Admin-blocked browser test not retried; no GitHub Actions run.
- **Next `ㄱ`:** authorized new screenshot/sanitized DOM intake and behavior claim validation, or evidence intake guard improvements if user capture unavailable. Existing `GenerationContract` remains `blocked_pending_review`.


## 2026-10-18/19 KST — p4 local capture intake and claim linkage

- Added `astra_contracts/capture_intake.py`, 32 new tests, `docs/CAPTURE_INTAKE_V01.md` and three **fictional** fixtures. Source commit `bb366f39bfd470dd445d718f64e5602795c0317a` on feature branch `feature/observation-contract-20261018`.
- New operator-file request binds known observation IDs to a SHA-pinned original bundle, records each local file's SHA, size and metadata in a separate pending-review manifest. Reads only explicit local files; copies to an **empty guarded temp folder** with exclusive file creation. `verify` checks registered files but not origin/semantics. No bundle certainty upgrade or actual code generation.
- **Local validation:** 302/302 pytest PASS (previous 270+32), compileall PASS. Synthetic DOM fixture register+verify: 1/1 local byte match, original bundle unchanged. In final suite one preexisting httpx deprecation warning; missing-manifest test expectation corrected to ValueError.
- **No real capture** acquired in this run. Screenshot origin/actual UI behavior/formula, human identity, customer DB/API and browser E2E unverified. Production preflight remains `blocked_pending_review`; no GitHub Actions or Vercel. Main remains `dc23ee604d02513c890615a3a98440c1ea8a5270`.
- **Next ㄱ:** separate human capture review/visual claim triage after authorized real evidence, or safe claim-review mechanism without semantic promotions. Overall ~37–38%; no material change to the original 7-step completion estimate.

## 2026-10-19 KST — p4 capture-to-claim manual triage

- One bounded unit implemented: `capture_claim_review.py` plus 23 new tests and `docs/CAPTURE_CLAIM_REVIEW_V01.md`; source commit `24d9b073c498b940df761a0c2716d029ed67e2b4`.
- A **registered** temporary capture folder and immutable source observation JSON produce a provenance-linked review packet after file/hash/association checks. Missing, stale or tampered evidence blocks. Reviewer decisions are unverified, not origin or behavioral proof, and do not change source certainty or grant approval.
- **Local:** 325/325 pytest PASS (302+23), compileall PASS, synthetic DOM CLI register→packet→record successful; all new Git blob hashes match tested code/doc. Historical screenshots/real user captures unavailable.
- Original URL semantics, formulas, reviewer identity, GUI browser E2E, customer DB/API and production remain unverified/untouched. GitHub Actions and previously blocked Chromium not run. `GenerationContract` continues `blocked_pending_review`; `main` unchanged.
- **Next `ㄱ`:** visible-state facts versus interaction/formula assertions classifier/review gate, or check newly supplied authorized real captures. Total progress remains about 37–38%.

## 2026-10-19 KST — p4 evidence assertion levels / manual review gates

- Implemented `evidence_claim_levels.py`, 24 new tests and `docs/EVIDENCE_CLAIM_LEVELS_V01.md` (code commit `a9c000ce107733e8b9cad788a012b4d4e1476f57`). Distinct `visible_state`, `interaction_transition`, `calculation_formula` gates after rechecking registered capture byte integrity and observation IDs.
- Screenshots/DOM are **only candidates for human displayed-state inspection**. A reported sequence additionally needs manual demonstration/test evidence + action + changed shared before/after state and non-unknown claim. Formula always requires independent audit, never approved through captured text/numbers alone.
- **Local:** full regression **349/349 PASS** (325+24); compileall PASS; synthetic fixture produced 6 review lanes. One unrelated existing httpx deprecation warning. No real captured source, human authenticated review or GUI browser E2E.
- **Safety:** no original ObservationBundle changes, source URL access, real data/DB/API integration, deployment or GitHub Actions. Current `GenerationContract` still `blocked_pending_review`; authority flags all false. `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` preserved.
- **Next `ㄱ`:** tiny end-to-end user-permitted manual action trace → functional spec → independent synthetic acceptance path; progress **~38%** (not a meaningful increase).

## 2026-10-19 KST — p4 first single-command fictional manual action pipeline

- Implemented `manual_trace_pipeline.py` + 24 new tests, complete safety/CLI doc, and 3 **fabricated** fixtures. Code source commit `acf2eaa11f8c7ce5aa9ef996e126e4d6dcd0f5e7` on isolated feature branch.
- One local operator-claimed manual-test trace is compared byte-safely and field/type-exactly to its referenced observation, then `derive_spec` → `compare_mappings` → `preflight_contract` (**blocked**) → `generate_bridge_preview` (8 fictional files) → `check_generated_preview` (12 synthetic checks) → 9th non-executable JSON result. No source behaviors/formulas converted into real executable business logic.
- **Local 373/373 pytest PASS**, compileall PASS, real CLI run and self-contained generated SQLite checks PASS. Negative tests cover tampered/mismatched traces, fake approvals, wrong stack/schema, path guards and source immutability. New six Git blobs match locally tested file SHA. One unrelated old httpx deprecation warning.
- No real website capture, actual user demonstration, owner DB/API, application merge, deployment, Actions, GUI browser or permission. `GenerationContract.status=blocked_pending_review`, all authorization/production flags false. `main` and existing apps unchanged.
- **Next `ㄱ`:** one bounded feature-acceptance adapter or first approved real source trace with proper independent evidence, not a generic production app. Estimated overall ~40%, prior ~38% (not a material +5 percentage point increase).

## 2026-10-19 KST — p4 fixture-only feature acceptance adapter

- Added `feature_acceptance_adapter.py`, 34 tests, operator-authored eight-case synthetic plan fixture, and `FEATURE_ACCEPTANCE_ADAPTER_V01.md`.
- Connects exactly matched, SHA-pinned fictional manual action/observation and prior generated preview to independently declared list/search/filter/detail expectations. Each case is explicitly either a **single illustrated source feature** or an **unrelated synthetic fixture test**. No falsely inferred original feature coverage.
- Runs prior generated-preview integrity and 12+ synthetic checks, then tests eight specifically expected API responses (ordering, limit, Korean text, literal wildcard, category match/no-match, detail 200/404) on a separate disposable SQLite DB. **407/407 full local pytest PASS**, compileall PASS; one preexisting unrelated httpx warning.
- Rejected forged approvals, wrong observation/feature IDs, stale hashes, tampered generated templates/seed, malformed cases and false expectations. Real source UI, production schema/DB/API, browser graphical UI, business formulas, CRUD and deploy are **unverified/not implemented**. `GenerationContract=blocked_pending_review`.
- Branch `feature/observation-contract-20261018`; `main` unchanged; no GitHub Actions or blocked Chromium reattempt. Progress ~41–42% (not material +5%p). Next: independent synthetic schema-shape adapter or authorized real trace validation.

## 2026-10-19 KST — p4 schema-aware synthetic acceptance reuse

- Added `schema_reuse_adapter.py`, 40 tests, full doc and product/ticket fictional fixture-and-acceptance pairs. The identical list/search/filter/detail acceptance machinery now runs against **two physically different explicit column sets**, normalized to a four-field fixed synthetic demo interface.
- **447/447 regression tests PASS** (407 old +40 new), compileall PASS; products 6/6 and tickets 7/7 direct functional cases PASS. Actual local Uvicorn for both generated apps returned 200 filter/detail, 404 for missing ID. New seven Git blobs exact-match local tested sources.
- Rejects stale physical schema SHA, bad columns/types, mismatched expected ID ordering, fake original-feature attribution, real/owner schema, invented consent, nonempty/outside destination. No arbitrary DB query/codegen, original URL capture, customer data or permissions. `GenerationContract` remains `blocked_pending_review`; `main`, /shop, /jobs and other projects unchanged. GitHub Actions and blocked browser not retried.
- Overall ~43% (prior ~42%; no +5%p change). **Next `ㄱ`:** extend logical operation coverage on deliberately fictional fields, or another grounded reproducibility test; only report production gain when actually shown.

## 2026-10-19 KST — p4 synthetic sort and physical-field typed filter

- New read-only schema_query_extension.py FastAPI /api/rows supports two explicit fictional physical schemas (products/support tickets) without guessing names. Whitelisted sort fields, asc/desc, exact typed string/int equality filters, limit 1–100, stable tie-break. Does not query a customer database or change generated app/main.py template.
- Full regression 477/477 pytest PASS (447+30), compileall PASS; products 9/9 + tickets 9/9 query contracts PASS; actual localhost Uvicorn 200 valid sorted/filtered responses, 422 invalid field, both schemas.
- Five new Git blobs match tested local content. No GitHub Actions, blocked browser retry, real URL, owned DB/API, production or site semantics. Authorization flags false and GenerationContract remains blocked_pending_review.
- main dc23ee604d02513c890615a3a98440c1ea8a5270 preserved. Overall ~44% vs prior 43% (not +5%p).
- Next ㄱ: mount optional read-only query router into verified generated synthetic app and test actual artifact; no real DB access.

## 2026-10-19 KST — p4 generated-app embedded typed queries (one bounded unit)

1. **Goal and code:** Integrated the previously standalone fictional physical-column sort/equality-filter API INTO the generated synthetic FastAPI application through an optional `app.extended:app` entrypoint. New `astra_contracts/schema_query_embed.py`, `tests/test_schema_query_embed.py`, `docs/GENERATED_QUERY_EMBED_V01.md`. Existing protected `app/main.py`, `app/index.html`, original generator and SQLite routes unchanged; old `app.main:app` still works.
2. **Scope:** Fixed self-contained generated Python router; SHA-pinned fictional physical table fixture (four explicitly bound columns), 1–100 limit, strict typed equality filters, stable asc/desc sort; no SQL from untrusted inputs. Generated project includes `app/extended.py`, `data/query_physical_fixture.json`, `data/query_cases.json`, `tests/test_embedded_query.py`, `README_EXTENDED.md`, and passing report `data/query_embed_report.json`. No import of the ASTRA source package in the generated app.
3. **Validation:** Local Python `python -m pytest -q tests/test_*.py`: **501/501 PASS** (previous 477 + 24 new), one pre-existing httpx deprecation warning. `python -m compileall -q astra_contracts tests` PASS. Both product and ticket fictional schemas: generated project's own tests PASS, 9/9 query acceptance each. Actual loopback `uvicorn app.extended:app` for BOTH: valid sort/filter 200; undeclared field 422; old list 200; old nonexistent detail 404. A file-change or symlinked fixture blocks loading; source templates unchanged. CLI one-command wrapper tested.
4. **Source commit:** `33819e2b95b3b204990b4250bd6ccad8907e62f5` parent `7c476122920b2c45eb2ec7b663e22c63ce1cb3de` on `feature/observation-contract-20261018`. Exact source Git blob `470849942ecae1297543965665f77a9c64bf073e`; tests `0a119b1cacd4d6f2dfb6044c336826a9153c36f6`; docs `59513f44bc347910341fe6f5be885e749b5c4102` — matching locally tested byte content.
5. **Artifacts:** Conversation ZIP `/mnt/data/astra_p4_generated_extended_preview_20261019.zip` holds runnable generated synthetic app; local verification JSON `/mnt/data/astra_p4_embedded_query_verification_20261019.json`. Reports cannot verify reference URL behavior or permissions.
6. **Safety:** Existing production `GenerationContract.status=blocked_pending_review` unchanged. No real website visit, actual captured source behavior, customer DB/API, unknown column inference, CRUD, private source copying, credentials, deployment, GitHub Actions or admin-blocked browser retest. New generated project stays in `astra-synth-*` system-temp directory, original `main` remains `dc23ee604d02513c890615a3a98440c1ea8a5270`.
7. **Next exact `ㄱ`:** Implement one safe, disposable **synthetic CRUD** proof with explicit schema and isolated SQLite transaction assertions, or add read-only typed query UI controls to the new optional frontend. Do not connect owner DB without separate consent; no generalized URL→production app claim.
8. **Overall estimate:** conservatively about **45%** (previous ~44%; less than meaningful +5 percentage points); independent generated app now actually serves its own optional typed query route, but real site mapping, owned DB integration, production-ready generation remain incomplete.

## 2026-10-19 KST — p4 synthetic CRUD proof (one bounded unit)

- Added `astra_contracts/synthetic_crud.py`, `tests/test_synthetic_crud.py` and `docs/SYNTHETIC_CRUD_V01.md` to the isolated feature branch, commit `513ceb1b4ab8af17b4ddf0a6e69745d7507251d7`.
- Exactly three blobs byte-identical to local code/test/doc via git object SHA: `93c8182117e6192603f93af69407ff4f23a99289`, `3a658bce7fbe3a2175d87c3d42442c91541c8aa7`, `32c5c6c1955f0e90da2ee9443fb4c0b2c47c44d6`.
- Direct synthetic CRUD tests: **14/14 PASS** (fresh rerun). Full-suite rerun progressed to ~97% but hit tool time limit; **full-suite PASS NOT asserted**. Previous baseline 501/501 PASS predates this new unit.
- Safety constraints: SQLite file must be fresh, nonexistent, not symlinked, directly inside an `astra-synth-crud-*` system-temp directory; strict field/type validation; read/create/update/delete only fictional records; invalid patch/extra fields/duplicate IDs rejected.
- Not embedded in generated app; no original-site or owner DB reads/writes; auth/preflight remains `blocked_pending_review`; original `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged. Github Actions and blocked browser were not run.
- **Next `ㄱ`**: complete segmented regression and integrate guarded CRUD only into an isolated synthetic generated preview; no real customer DB without explicit authority. Estimated overall progress remains **~45%** until integrated end-to-end validation.

## 2026-10-19 KST — p4 optional synthetic CRUD integrated in GENERATED app

1. **Delivered**: `astra_contracts/schema_crud_embed.py`, `tests/test_schema_crud_embed.py`, `docs/GENERATED_SYNTHETIC_CRUD_INTEGRATION_V01.md`. Fixed `app/full.py` mounts strict `app/sandbox_crud.py` only under `/sandbox/api/items`, opt-in via exact `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY`; normal startup has no mutation routes. Independent disposable temp SQLite; `app/main.py`, HTML and read-only `app/extended.py` protected, unchanged.
2. **Validation**: segmented, complete **532/532 pytest PASS**: groups 137+125+103+130+37. Python compileall PASS. New schema_crud_embed suite 17 PASS (both products and tickets). Actual loopback Uvicorn HTTP in both generated applications and both opt-in/off modes: original read/query 200; unauthorized original POST 405; sandbox off 404; opt-in insert 201, read/update 200, duplicate 409, delete 204, missing 404. One unrelated existing httpx DeprecationWarning.
3. **Safety**: strict original generated-template and hash/contract verification before writes; rejects forged deployed permission claims, tampered extensions, symlink or existing output, non-temp output. Never touched actual source website or owner DB/API. `GenerationContract` remains `blocked_pending_review`, original-behavior verification, production readiness, and code/deploy authority all FALSE.
4. **Integrity**: tested new Git blob SHAs: source `e973c0bf3e0d18c0d29412965c0a4fad322dc33e`, tests `0465c5949ebfde259184e253cf7846744693b7ab`, doc `1a0ac502d4ad8b3c0b61b353b0a428c0038c221b`; commit `517b33b0b190e26820d97c8a05bb68ac55d1a59c`. Feature branch only; `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unmodified. No Actions nor blocked browser.
5. **Artifacts**: `astra_p4_generated_crud_preview_20261019.zip` and `astra_p4_crud_http_verification_20261019.json` in the active conversation workspace (not customer-data archives). Generated preview has JSON endpoints, no CRUD editor visible in HTML. Do NOT deploy unauthenticated opt-in sandbox or publicly expose it.
6. **Next bounded task**: Add usable sorting and typed filtering controls to generated *synthetic* HTML frontend (against its explicit schema), keeping protected original templates and strict safety contracts. No real customer-data access without authorization.
7. **Overall estimate**: conservative ~46%, up from ~45% (<5 percentage-point meaningful threshold); broad URL→owner DB→production app remains unimplemented.

## 2026-10-19 KST — p4 generated synthetic sort/filter UI (bounded unit)

1. **Scope:** Added `astra_contracts/schema_query_ui.py`, `tests/test_schema_query_ui.py`, `tests/ui_dom_simulation.cjs`, `tests/test_ui_dom_simulation.py`, and `docs/GENERATED_SYNTHETIC_QUERY_UI_V01.md`. Existing generated synthetic preview gains optional `app.ui:app` entrypoint and separate `/preview` read-only HTML page; four explicitly declared physical columns drive ascending/descending sort and exact string/int filtering, and `/api/preview-schema` serves schema labels. Original `/`, `app/main.py`, `app/index.html`, and CRUD sources unchanged.
2. **Validation:** Fully partitioned local pytest suite **557/557 PASS** (prior 532 plus 23 new generated-UI tests and 2 DOM simulation tests); compileall PASS. Two fictional physical schemas product (3 rows) and ticket (4 rows); real loopback Uvicorn/httpx `/preview`, schema, sort/filter 200, invalid physical column 422, original write 405, sandbox off 404; product text filter 2 rows and integer filter 1; tickets text filter 3 rows and integer filter 2. Node.js DOM *simulation* executed actual embedded JS controller for both schemas. Chromium navigation `net::ERR_BLOCKED_BY_ADMINISTRATOR` on 127.0.0.1; **browser render and actual click verification unperformed**, blocked URL not retried.
3. **Safety:** New code installs only into existing verified `astra-synth-*` temp preview with trusted prior query+CRUD reports, rejects tampered/symlinked/existing outputs, verifies static UI and physical fixture hashes at runtime, escapes query params via URLSearchParams and populates cells with textContent. Sandbox CRUD defaults disabled. No real source website, owner DB/API, credentials, production authorization, or arbitrary source-code copying; GenerationContract remains `blocked_pending_review`.
4. **Git integrity:** Functional commit `d1f9f28a4f631aecf1744e0f37a3c87a955bfe15`; 5 blobs match local git hash-object: source `14c4e1cb937925ecfecf25290279145b344e9864`, tests `98727cfc8f8e6a2bbaaf82e60b793c7a81afbc61`, DOM harness `f94f9b495588aff490c92be57f6eadb77aeca928`, DOM tests `59a179ccdf14b3fc2e7515350813cfb3a1ca15de`, docs `da7ca9d9b044ae019692ec4a03d2c1ab5c1a8555`. Feature branch only; original main `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged. No GitHub Actions.
5. **Artifacts:** `/mnt/data/astra_p4_generated_ui_preview_20261019.zip`, `/mnt/data/astra_p4_live_ui_verification_20261019.json`. `python -m uvicorn app.ui:app --host 127.0.0.1 --port 8017`, browse `/preview` on an authorized local machine; never deploy the unauthenticated demo.
6. **Next `ㄱ`:** Move from purely fictional app widgets toward a bounded observed-feature → explicit UI-field mapping contract with evidence requirements, or complete human browser smoke test on the operator's authorized local browser. No real owner DB connection until separately authorized. Conservative overall estimate **~47%** (prior 46%, below +5pp update threshold).

## 2026-10-19 KST — p4 evidence-to-UI traceability review v0.1

- Feature commit `34f35f4d770e17b6190c84ebc2ca661384dd0ee9`: new source/tests/doc + 12 fixtures = 15 exact local-to-Git SHA blobs. Offline `ObservationBundle` + declared synthetic schema + fictional physical table + hash-pinned link plan → per-link blocked/candidate report for read-only `/api/rows`.
- Fictional product filter `family=colors` 2 rows and ticket filter `lane=Open` 3 rows passed TestClient. Historic nail-brand archive blocked `archived_secondary_only`: no independently replayed click evidence. Hashed file bytes are *integrity*, not evidence authenticity.
- New tests **42/42**, entire regression partition **599/599 PASS** (557 unchanged prior +42 new); compileall PASS. No browser retest, owner DB/API, observed real reference behavior, authorization, CRUD changes, or generated-app UI changes. `GenerationContract=blocked_pending_review`; main unchanged. Status **~48%** vs 47%.
- Next: isolated synthetic UI manifest consumption gated by strict evidence linkage and human review; production URL→owner DB→app not complete.

## 2026-10-19 KST — p4 offline mapping review integrated into fictional generated UI

1. **Functional commit:** `a902b98c6fc4983f4e52f44dfed189dd02a42fa4`; new `mapping_review_ui.py`, `tests/test_mapping_review_ui.py`, Node DOM harness/wrapper, `docs/GENERATED_MAPPING_REVIEW_UI_V01.md`. Five Git blob SHA-1 values were verified byte-for-byte against tested local files.
2. **What is new:** standalone generated `app.mapped:app` with `/preview-mapped` and `/api/review-manifest`. Uses prior hash-bound operator report → explicit schema → fictional physical field mapping. Product `family=colors` / tickets `lane=Open` are still *unapproved synthetic illustrations*. Archived secondary brand observation appears **blocked**; every mapping action in HTML and JSON has `enabled=false`. Generic existing fictional query UI remains usable and independent, but no mapped observation is auto-applied.
3. **Validation:** New integration/negative tests **20/20 PASS**, Node DOM validation **2/2 PASS**; combined new **22/22 PASS**. Existing initial regression batch **262/262 PASS**. The remaining all-suite rerun repeatedly timed out due to long-running app fixture/subprocess tests; **621/621 PASS NOT claimed**. Previous baseline 599/599 was a separate prior completed run. Python compileall PASS. Existing generated product ZIP successfully extended with fixed review UI, and actual local Uvicorn `127.0.0.1` HTTP checks: `/health`, `/preview`, `/preview-mapped`, `/api/review-manifest`, read-only 2-row filter all 200; sandbox CRUD 404; original POST 405. Actual Chromium visual/click verification still blocked by administrator; not repeated.
4. **Safety:** Detects stale observation/declaration/table/evidence SHA, reports possible only for fictional data, validates the preexisting protected UI and data template byte-for-byte, refuses preexisting/symlinked output. New mapped mode explicitly refuses `ASTRA_ENABLE_SYNTHETIC_CRUD=YES_TEMP_ONLY` rather than exposing unauthenticated writes. Fixed review JS uses `textContent`, disabled buttons, no automatic `/api/rows` call from mappings; mapping JSON/HTML are SHA-pinned at HTTP serving time, tampering returns 503. `GenerationContract=blocked_pending_review` stays unchanged. No actual reference source, customer DB/API, credentials, deploy, GitHub Actions or blocked browser retries.
5. **Preservation:** `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged; feature branch only. Fixed original app templates and read-only API untouched. Local sample `astra_p4_mapping_review_preview_20261019.zip`, `astra_p4_mapping_review_http_20261019.json`.
6. **Next `ㄱ`:** Collect/validate explicitly authorized first-hand reference UI before/after capture, or build a clear provenance reviewer ledger; do not silently upgrade archived or operator-reported claims. True URL→owner DB/API→functioning production app remains unproven. Overall ~49% planning estimate (prior 48%, less than meaningful +5 percentage points).

## 2026-10-19 KST — p4 offline before/after capture pair ledger

1. **Feature commit:** `85e2ffb6cde5693b9a27f6c7ec1ccec99d3bd121` on `feature/observation-contract-20261018`, 8 new files: `astra_contracts/capture_transition_ledger.py`, `tests/test_capture_transition_ledger.py`, `docs/BEFORE_AFTER_CAPTURE_LEDGER_V01.md`, three synthetic observation/intake/plan fixture JSONs and two fictional DOM snapshots. All 8 blob SHA-1 values were checked against locally tested `git hash-object` output; no unrelated files modified.
2. **Behavior:** Reuses offline capture intake and human triage byte-integrity checks, validates pinned observation/intake manifest hashes, two distinct locally supplied snapshot IDs tied to the same observation, timezone-aware chronological order, stated action and changed scalar field. Produces review-only statuses, including `paired_bytes_present_unverified`; rejects stale hashes, unknown/unlinked IDs, symlinks or tampering, forged approval flags, duplicate pairs. CLI emits JSON to stdout; no writes or network.
3. **Validation:** 27/27 new tests PASS, full **648/648** regression tests PASS as disjoint file-level / parametrized partitions (prior 621 + 27), `compileall` PASS. Some original combined test runs timed out and were replaced with complete non-overlapping partitions; no test case omitted from the 648 collected. Fictional example reproduces one structurally consistent pair with all authority and authenticity flags false. Artifact `astra_p4_transition_ledger_sample_20261019.json` in conversation workspace.
4. **Explicit limits:** Source site's click / screenshots **were not obtained**. Synthetic before/after DOM text is invented and is **not screenshot authenticity, independently verified behavior, semantic approval, UI enablement, owner DB permission or deployment**. Keep `GenerationContract=blocked_pending_review`. Existing generated mock UI mapping controls remain disabled. No Chrome reattempt, GitHub Actions, credentials, real-site access or customer DB/API.
5. **Preservation:** Baseline `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged; protected synthetic generator and preexisting fixtures unchanged.
6. **Next exact `ㄱ`:** Extend the **review-only** UI to read the provenance ledger and display which pairs are byte-consistent vs incomplete while keeping all controls disabled, or validate a narrowly authorized human local before/after capture if such original inputs actually exist. No site-authenticity promotion by inference. Conservative overall completion estimate **~49%** (unchanged; core real-URL→owner-DB→functional production app unproven).

## 2026-10-19 KST — p4 disabled transition provenance panel

- Functional commit `396926242e63d037c5549328ad0760268c6fa2a4`. Six new files: `astra_contracts/transition_review_ui.py`, Python integration tests, Node DOM simulator and wrapper, specification, and independent localhost HTTP script. All new Git blob SHA-1s match tested local content.
- Generates optional `app.transitions:app` with `/preview-transitions` and `/api/transition-ledger` in fictional-only temp preview. Retains previous query/mapping page, displays redacted before/after linkage and claim-consistency statuses, all actions permanently DISABLED. No raw snapshot data or claimed before/after values copied.
- Before install, the earlier evidence ledger is rebuilt and original byte-integrity hashes rechecked. SHA-pins new HTML/manifest and old protected mapped assets. Runtime asset tamper returns 503. Original capture source files are **not** rechecked on every HTTP response; provenance remains unauthenticated. Any CRUD write-mode opt-in refuses mapped/transition panel startup.
- New tests **32/32 PASS** (partitioned); adjacent previous tests **103/103 PASS**; compileall PASS. Actual 127.0.0.1 Uvicorn product/ticket integrations: new and old GET routes 200, original POST 405, disabled sandbox 404, filter results 2/3. Combined slow legacy pytest batch hit execution timeout: **cannot claim full 680/680 current regression PASS**. Baseline 648/648 from previous unit remains historical only. Chromium not retried.
- `main` `dc23ee604d02513c890615a3a98440c1ea8a5270` unchanged; no GitHub Actions, source site, owner DB/API, credential, real approval, production or public deployment. `GenerationContract=blocked_pending_review`. Overall estimate ~49% maintained.
- Next: obtain permissioned first-hand actual website observation and independently assess state change/semantics, or test a known public sandbox site. Avoid continued UI-only inflation.
