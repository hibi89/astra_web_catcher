# ASTRA Step 2 — ONE archived brand-filter case converted to evidence JSON

- **Purpose:** a reusable observation bundle, not a nail-specific backend or a claim that the original site's implementation was discovered.
- **Source of truth:** `research/jp-nail-dashboard/BRAND_FILTER_OBSERVATIONS_2026-10-18.md` on `research/jp-nail-dashboard-20261018`, original Git blob `b9d676e0e7ba8af2124a0785e8c57b9ab6195f1b`.
- **Self-contained provenance pointer:** `evidence/jp_nail_brand_filter_source_20261018.md`. It links to the immutable source and explicitly says original user screenshots / DOM are not stored or reverified in this branch.
- **Converted machine-readable observation:** `fixtures/jp_nail_brand_filter_observation_20261018.json`. One brand ALL/OHORA comparison with exact displayed KPI values; two `unknown` claims about calculation rules and filtering internals. No click event is inferred, and the unrelated NAILTOWN DOM state is excluded.
- **Minor evidence-contract extension:** `archived_report` means the linked artifact is secondary historic documentation, **not** screenshot or replayable browser evidence. Existing v1 fields and categories stay compatible.

## Verification from repo root

```bash
python -m pytest -q tests/test_observation_contract.py tests/test_jp_nail_archive_conversion.py
python -m astra_contracts.observation validate fixtures/jp_nail_brand_filter_observation_20261018.json
python -m compileall -q astra_contracts tests
```

Local verification (2026-10-18 KST): **27/27 PASS**, CLI reports **3 observations / 1 archived report**, compileall passed, Python 3.13, Pydantic 2.13.5, pytest 9. Existing /shop, /jobs, research and experiment suites and actual browser/network have **not been rerun** for this unit. Production not applicable.

## Acceptance boundaries

- Zero and null are distinct (`direct_application_posts: 0` for OHORA, unknown formulas: `null`).
- 153→79 analyzed, 194→94 collected, 526→629 average reactions, 101→78 Reels, 52%→83% displayed Reel share, 71→0 direct application, 82→79 sheets and run 3728 preserved from source.
- The report describes independently viewed screenshots. The conversion is **not evidence of a live filter call, real n8n API, original DB schema, screenshot availability, or exact formulas**.
- No new harvesting, cookies, credential material, original database changes, merge into main or production deployment.
- **Next `ㄱ`:** begin Step 4-B — derive a minimal machine-readable *functional specification* from validated UI observation cases with explicit unknowns and approval gates, not from guesses about a backend.
