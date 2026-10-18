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

## Dashboard observation research (2026-10-18 16:44 KST; isolated branch)

- Branch: research/jp-nail-dashboard-20261018, based on main dd87ffc847c7b435c7eed7b4543b7db7d184e08c.
- Document: research/jp-nail-dashboard/OBSERVATION_SPEC_2026-10-18.md.
- Connected browser tab DOM text: success. Web fetch: DisabledError. Sandbox HTTPS: DNS NameResolutionError. Neither proves source-site permission problems.
- Only initial page display observed, NOT filter/menu clicks, Network, DB, or n8n API integration.
- Formula and data source remain unverified; proposed models/endpoints are not original backend knowledge.
- Await 2–4 minute user recording/screenshots. Original main, two MVP apps, test code, and prior test outcomes preserved. Prior 13-pass suite was NOT rerun in this research phase.

## Follow-up brand filter observation: ALL / OHORA / NAILTOWN
- Recorded (KST): 2026-10-18 16:57:50. Evidence: two user-provided screenshots and read-only connected tab text, not automated click traces.
- `research/jp-nail-dashboard/BRAND_FILTER_OBSERVATIONS_2026-10-18.md` committed on isolated research branch as `dc11aa32099c746adb296fad03b58e85c6e1a7b3`.
- ALL: 153 analyzed / 194 collected, avg response 526, Reels 101 (52%), direct 71 / sheet 82.
- OHORA: 79 analyzed / 94 collected, avg response 629, Reels 78 (83%), direct 0 / sheet 79.
- NAILTOWN (connected tab): 49 analyzed / 61 collected, avg response 217, Reels 9 (15%), direct 49 / sheet 0.
- Brand selection correlates with updates to KPI, weekly chart, content response ranking, posting-hour distribution, post-type donut and right-side brand panel. Screenshots demonstrate differing states, not underlying filter algorithm.
- Still unknown: exact formulae, source API vs static JSON, click event trace, tag analysis/brand comparison/top posts interactive details.
- Next: user announces each tab/filter click; read browser again, compare with baseline, append observation, then produce gap list before any dashboard implementation.
- Existing `/shop` and `/jobs` and previous integrity test results preserved. No new tests run in this documentation update.
