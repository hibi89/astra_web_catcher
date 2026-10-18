# OHORA training capture → isolated Nail Atlas experiment

**Execution:** 2026-10-18; exploratory data, not production or validated trend analysis. Existing two MVPs and validated `nail_dashboard` frozen snapshot were **not modified**. Original ZIP source hash was unchanged.

### Source (local only)

- `OHORA_Analysis_Ready_20261016_084112.zip` SHA-256 `bc77130e89050c303502d6c88f2b37cc823bc7be28eed1de6b1d76a2e0a9d7d3`
- Archive contents read: accounts_coverage.csv, posts_flat_for_analysis.csv, media_merged.csv. The original RAW ZIP remains separate.
- **Do not commit the archive or generated SQLite practice DB to GitHub.** The SQLite staging copy strips usernames, captions, post URLs, media URL data and image URLs.

### Verified import (separate local SQLite)

| Check | Result |
|---|---:|
| Accounts | 294 |
| Collected accounts | 286 |
| Failed accounts | 8 |
| Post rows | 1845 |
| Media rows | 5953 |
| Posts with nonmissing likes+comments | 1224 |
| Posts with unknown likes | 621 |
| Account↔post↔media foreign-key errors | 0 |
| Duplicate post and media IDs | 0 |

Country totals JP 910 / KR 485 / US 450 posts. Observed reactions with both operands present: JP 579, KR 292, US 353. Missing reactions JP 331, KR 193, US 97. Country differences are **capture sampling bias**, not consumer demand differences. Post age dates span more than three years and capture depths vary.

### Tests actually run

- `OHORA_PRACTICE_ZIP=/mnt/data/OHORA_Analysis_Ready_20261016_084112.zip python -m pytest -q nail_practice/tests` → **16 passed** (includes real archive opt-in integration, other tests use generated temporary ZIP+DB).
- `python -m compileall -q nail_practice` → PASS.
- `node --check nail_practice/static/app.js` → PASS.
- Actual Uvicorn HTTP server (separate port 18011 in validation sandbox) → HTTP 200 on `/practice`, `/api/practice/report`, `/api/practice/overview?country=JP`, `/api/practice/countries`, `/api/practice/posts?country=JP&page=2`, `/api/practice/accounts?status=failed`.
- Browser E2E script included for user's Windows: `python -m nail_practice.tests.browser_e2e`; **not executed in validation sandbox**.

### Interpretation

This demonstrates a working experimental dashboard based on captured account/post/media statistics, not a verified AI-designed gel-nail trend recommender. No post views, reliable design tags, trend demand/purchase probabilities, live Meta API or n8n integration. No transformation of account rows into brands, and no interpolation for missing likes. Original source untouched.
