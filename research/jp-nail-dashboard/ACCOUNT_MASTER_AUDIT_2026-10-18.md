# OHORA account master — read-only CSV audit (2026-10-18)

## Source and preservation

- User supplied `account_list(2).csv` in this chat; analyzed **read-only** by Python standard library `csv.DictReader`. The CSV is an **account master list**, not a post dataset or brand model.
- Original bytes: 117,181; SHA-256: `fb539da915034df23fd6faccd598cc4caf7feaba631f9f8351c1afa2b88c2e8c`. Rehashed before and after inspection; unchanged.
- **Do not commit raw CSV, account usernames or image URLs to GitHub**. This note stores only aggregate QA findings, source filename/size/hash/column names.
- Protected tested B MVP: `snapshot/nail-atlas-b-e2e-verified-2026-10-18` at `343790e34967f0b20862d4ec7f5de8f084414234`; existing `main`, `nail_dashboard` source, user/seed DB and external datasets untouched.

## Header and structural checks

- Exactly four columns: `account_key`, `username`, `country`, `image_url`.
- 294 records excluding header. CSV rows parsed without excess columns; all four columns populated on every record; no leading/trailing whitespace observed in the four fields.
- Duplicates: `account_key` 0 duplicate groups, `username` 0 duplicate groups, `(account_key, username)` 0 duplicates, full identical rows 0 duplicates. Unique count: each column except country has 294 distinct values; country has 3 distinct values.
- Key format: all 294 `account_key` values match `XX_NNN`; country prefix matches `country` 294/294; per-country sequences contiguous with no gaps from 001 through maximum (KR 100; US 101; JP 93).
- `image_url`: present and begins `https://` in 294/294; neither URL accessibility nor validity was tested; do not access/fetch content.
- Blank/null missing cell count: 0 across 1176 inspected cells. Note: this is a **field blank check**, not proof every desired account is present in the external world.

## Country distribution (master account counts; not brand, post or reaction counts)

| Country | Accounts | Share |
|---|---:|---:|
| US | 101 | 34.35% |
| KR | 100 | 34.01% |
| JP | 93 | 31.63% |
| **TOTAL** | **294** | **100% (rounding)** |

Shares from row count divided by 294, rounded independently to 2 decimal places; rounded shares sum to 99.99%.

## Data contract and limitations

- Current CSV **only establishes a set of account keys, usernames, country codes and optional profile image links**. Do not insert 294 synthetic rows into `brands` or `posts`, and do not conflate account, brand and post levels.
- The existing B MVP SQLite model has `report_runs`, `brands`, `posts`, `tags`, `post_tags`. This file does not provide `posts` rows, post/reaction/view data, the post-to-account foreign key, report collection period, post timestamp or classification/analysis flags.
- Accordingly, analyzed/collected **post** counts, likes/comments, engagement/response, median/mean, reels share, trend series, tag demand and brand performance indicators are **not computable / insufficient input data**. Account count 294 is separately known but not usable as a post count.
- No schema/code changes; no DB inserts, overwrites, `seed --reset`, API integration or guessed post-brand mapping.
- Additional post CSV/API dump has **not been provided with this user message**. Availability of any separately held post file is **unconfirmed**, so large dashboard restructuring is deferred.
- Next minimal input: user confirmation whether there is a separate **posts file** and, if available, just anonymized **column names and 5–10 example rows** for post→account linking and metrics feasibility (no full raw data or secrets).

## Execution

- Source file inspected with Python stdlib CSV, collections and SHA-256. Static duplicate/missing/distribution/gap checks only; no live Instagram/Meta requests. No changes to user supplied input.
