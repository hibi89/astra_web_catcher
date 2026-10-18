# Nail Atlas OHORA practice dashboard — isolated experimental build

**Exploratory build only.** Does not modify `nail_dashboard/`, existing app and job marketplace MVPs, frozen Git snapshot, source ZIPs, or any user DB. The real CSV data stays local and **is not committed to GitHub**.

## Windows PowerShell (from cloned repo root)

Keep `OHORA_Analysis_Ready_20261016_084112.zip` in Downloads; it is used read-only.

```powershell
python -m pip install -r requirements.txt
python -m nail_practice.import_data
python -m uvicorn nail_practice.app:app --host 127.0.0.1 --port 8011
```

Open **http://127.0.0.1:8011/practice**. API docs: **http://127.0.0.1:8011/practice/api-docs**.

If archive is elsewhere:

```powershell
python -m nail_practice.import_data --zip "C:\PATH\OHORA_Analysis_Ready_20261016_084112.zip"
```

`import_data` **refuses to overwrite an existing practice DB**. To repeat with another sample, use a new DB path, and point the independent app at that DB in a future update; don't delete or overwrite source. The import copies only pseudonymous account keys, opaque post/media identifiers, country codes, timestamps and numeric metrics. It intentionally drops usernames, captions, Instagram URLs, image URLs and media links. No external network requests, AI inference or n8n workflow is run.

## Four experimental menus

1. Dashboard: country filter; real rows/KPIs, last 13 weeks captured post counts, media type, KST hour counts. This is **sample composition**, not verified market trends.
2. Country comparison: 3 national account/post/media/reaction-coverage metrics. Different per-account capture depths (1/5/10) preclude clean country ranking.
3. Account status: actual 294 master entries, 286 collected, 8 failed. Account ≠ brand.
4. Top posts: observed reactions (likes + comments where both available) sorted descending, 15/5 pagination, country change resets page 1. Missing reaction posts are excluded from ranking and separately counted (not silently treated as zero).

Null ratio denominators produce null API values, displayed as `—`. No views, design tag labels or genuine demand/purchase/performance scores are computed. Re-fetch control **only reloads local DB**.

## Tests

```powershell
python -m pytest -q nail_practice/tests
```

To add real ZIP check on Windows:

```powershell
$env:OHORA_PRACTICE_ZIP="$env:USERPROFILE\Downloads\OHORA_Analysis_Ready_20261016_084112.zip"
python -m pytest -q nail_practice/tests
```

Tests create **new temporary SQLite files**. The original raw / analysis ZIP archives and other database files are never modified.

## Scope and gaps

This is an explicitly separate **practice adaptation** of the previously verified B MVP, not an integrated user data connection for the production Nail Atlas dashboard. Before tomorrow's full capture, standardize countries' date windows / samples per account and preserve collection status plus NULL/0 distinctions. Only once actual classification/metrics definitions exist should the main dashboard's data adapter be planned.
