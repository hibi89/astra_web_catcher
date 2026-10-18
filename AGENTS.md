# Astra Web Catcher — Development Rules

- This repository is the intended code/version source of truth; do not confuse a locally generated ZIP with a GitHub push.
- Preserve existing working functionality and user data; back up before destructive migrations.
- Work in small vertical slices: UI → own API → DB → tests. Do not clone original site assets or use private APIs.
- Browser observation must be attributed only to pages actually inspected. Never bypass login, CAPTCHA or rate limits.
- All authentication decisions are server-side, based on HttpOnly session cookie. Filter private data by session owner.
- All financial amounts in integer won, order line snapshots immutable. Preserve `BEGIN IMMEDIATE` plus conditional stock decrement.
- Maintain unique constraints for cart, request keys, bookmarks, applications. Test parallel requests against separate SQLite DB.
- Never use production credentials or payment details. Demo accounts are for localhost only.
- Record actual test command/status, not assumptions. Browser automation blocked is a limitation, not a pass.
- On meaningful change update README/ARCHITECTURE/TEST-REPORT/REVIEW-PACK, STATUS.md and HANDOFF.md, then GitHub when supported.
