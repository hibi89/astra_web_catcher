# P4 ASTRA — synthetic owner-shaped mapping and cross-owner SQLite isolation (2026-10-19)

## Scope and design

A bounded proof of the *mechanism* of an owner-shaped declared schema → 4 explicitly proposed time-series semantic bindings → **one shared** disposable SQLite \`:memory:\` table → **server-side session-scoped** read-only API and Chart/Table UI.

All sources/identities/measurements are invented: \`demo_alpha\`, \`demo_beta\`, 6 fabricated nail trend records, including a deliberately **colliding entity/period pair** (same SharedDesign and 2026-01 for both owners) and distinct canary markers and metric values. This is not a customer, OWID, OHORA, or production system.

Previous approach was two separate SQLite application instances. This unit intentionally changes the threat model: both synthetic owners share *one* SQLite connection and the same physical table, so every read must apply a server-controlled owner predicate.

| Component | Mechanism |
| --- | --- |
| \`examples/p4_owner_demo_schema.json\` | Explicit \`owner_binding=workspace_key\` and separate \`entity_identifier\`, \`time_period\`, \`numeric_measure\`, \`aggregation_semantics\` bindings; \`source_kind=synthetic_fixture\`; only demo-prefixed owner identities |
| \`astra_contracts/synthetic_owner_isolation.py\` | Validates exact five-column declaration, compatibility and unique owner mapping; partitions and validates owner-scoped rows; in-memory SQLite with \`PRIMARY KEY(owner_id, entity, period)\`; \`SELECT ... WHERE owner_id=?\`; JSON responses and Chart/Table HTML built only from that scoped snapshot |
| \`InProcessDemoSessions\` | Local test driver alone issues a random opaque token; server stores a hash→owner mapping; requests resolve only an HttpOnly cookie set by the test harness. Client headers, query parameters, URL path or raw owner IDs cannot create sessions or change the principal. No login/issuance HTTP endpoint exists |
| \`tests/test_synthetic_owner_isolation.py\` | 33 owner mapping, data isolation and rejection scenarios including IDOR, 401 anonymous/forged cookie, 404 cross-owner URL, response and HTML canaries, invalid mappings and row shapes, atomic in-process fixture change, case of identical keys owned by different tenants, SQL/HTML injection strings, app-instance and lifespan isolation |
| \`scripts/p4_owner_isolation_browser_smoke.py\` | Actual Chromium HTTP browser contexts with separate HttpOnly cookies, same localhost server, API fetch and Chart↔Table keyboard/click, blocked cross-owner URL, forged unauthenticated context, distinct views and SHA fingerprints, A-only synthetic data change not affecting B |
| \`.github/workflows/p4-owner-isolation.yml\` | Two independent CI jobs: complete offline repository pytest and real Chromium/loopback E2E; JSON browser report artifact contains **no raw sessions** |

## Actual executed checks

- Local Python 3.13.5 / pytest 9.0.2, exact working source: **33/33 new owner tests PASS**, old SQLite owner-independent API tests plus new **46/46 PASS**, relevant observation→chart/table→SQLite plus new **96/96 PASS**; Python \`compileall\` PASS.
- GitHub source blobs matched the locally tested bytes for the new module, 33 tests, browser script, and the two synthetic fixtures.
- GitHub Actions [run 39225637124](https://github.com/hibi89/astra_web_catcher/actions/runs/39225637124): **Real Chromium 156.0.8078.4 loopback HTTP job PASS**, with 33/33 direct pytest PASS. Actual browser tests: both owner-specific API/HTML views and three SVG points each; 404 cross-owner lookup and forged owner header; 401 anonymous or forged cookie; JavaScript \`document.cookie\` cannot access HttpOnly cookie; A-only update changed A SHA/display while B SHA/display stayed identical; Chart/Table click, Enter/Space; zero external requests and JavaScript errors. Artifact stored by workflow.
- **Full-repository CI result verified:** the SAME GitHub Actions run #39225637124 at code/workflow SHA `a6ddf780995b4f11c49edebdb7198e08cc4250c9` ended **completed/SUCCESS, 2/2 jobs success**. Ubuntu Python 3.13.16 entire repo `python -m pytest -q -ra tests` returned **940 passed, 2 skipped, 2 warnings, 0 failed in 92.31 seconds**; compileall PASS. The 2 skips are earlier evidence-ZIP-dependent tests (`test_chart_table_synthetic_bridge.py` and `test_synthetic_chart_table_preview.py`); they are NOT counted as passed in this CI. Real Chromium browser job 156.0.8078.4 PASS, with 33/33 new targeted tests PASS. Artifacts: [pytest JUnit #12174140752](https://github.com/hibi89/astra_web_catcher/actions/runs/39225637124/artifacts/12174140752), [browser JSON #12173004170](https://github.com/hibi89/astra_web_catcher/actions/runs/39225637124/artifacts/12173004170). Earlier full 894/2-skip belongs to the previous feature snapshot.

## Reproduction

Use only these synthetic fixtures; no credentials, external dataset, owner database or production resource needed.

    python -m pip install -r requirements.txt 'selenium>=4.27,<5'
    python -m pytest -q -ra tests/test_synthetic_owner_isolation.py
    python -m pytest -q -ra tests
    python -m playwright install --with-deps chromium
    python -m scripts.p4_owner_isolation_browser_smoke --schema examples/p4_owner_demo_schema.json --rows examples/p4_owner_demo_rows.json

The browser script starts Uvicorn bound **only to 127.0.0.1**, uses a single in-memory SQLite and random sessions, then closes the browser and server. It does not print tokens or expose login/write endpoints. The in-process synthetic fixture replacement capability is never exposed as an HTTP route.

## Approval and security limits

- **Synthetic isolation is not production authentication.** Cookie \`Secure\` is not enabled because this strictly local demo uses HTTP loopback; no real-login flow, CSRF-secured writes, durable session storage, tenant provisioning, access audit, rate limiting, security review, or HTTPS production policy is implemented. An HttpOnly cookie in Chromium does not by itself certify full production security.
- All mappings are \`structurally_compatible_unapproved\`, not semantically approved. Original OWID algorithm/data processing and any real owner fields are unverified.
- No deployment, main merge, API credentials, production database, external scraping, customer data, mutation of owner schema, or real data migration.
- \`generation_contract=blocked_pending_review\`, \`mapping_approved=false\`, \`owner_schema_connected=false\`, code generation/deployment authorization false.

## Next bounded step

Either a disposable **client-rendered** owner-scoped API → chart/table view with stale/cross-owner response rejection, or an explicit owner schema checklist/review gate, depending on the roadmap and permissions. Real owner data integrations need separate scope/approval and test on disposable copies; no assumed access to customer systems.
