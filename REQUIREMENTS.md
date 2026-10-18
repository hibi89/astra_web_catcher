# Confirmed Requirements

Origin: user request 2026-10-18 for two independent local MVPs based on *public user flows* of YES24 (book store) and Wanted (job postings). No code or service copying.

## BookHARBOR (`/shop`)
- Database-driven fictional products (>20) & categories (>4), stockout, integer KRW.
- Title/author search, category, price sort, pagination, product detail.
- Per-user cart merge/update/delete, stock validation.
- Demo order without payment or shipment; server price, atomic stock, rollback on shortage, request-key idempotency, order item price/title snapshot.
- Per-user order list/detail with A/B isolation.

## CareerWAY (`/jobs`)
- Fictional companies (>6) and jobs (>20), at least two closed.
- Search/role/region/experience/open filters (AND; experience means candidate years with inclusive min/max or any-career).
- Details, bookmark/unbookmark, note-based demo applications, duplicate & closed rejection, A/B isolation, my page and application detail.

## Common
- 2 demo accounts, session cookie login/logout, backend validation/error statuses, DB persistence across restart, query-string filters/page state.
- No registration, actual payments, resume files, external applications, real personal data or deploy by default.
- pytest with isolated test DB and parallel HTTP tests, browser if possible; docs and reviewer pack.
- User can submit browser recording/screenshots of ambiguous original flows; network traces must exclude secrets.

## Explicit deviations

Requested default Next.js+TypeScript+Prisma, but current sandbox could not resolve npm registry (`EAI_AGAIN`), so installed FastAPI+SQLite+vanilla JS used to deliver an executable local MVP today. This is a conscious substitution with incomplete technology-specific acceptance criteria. Browser executable exists, but navigation to localhost was blocked by Chromium administrator policy. A full E2E browser pass is pending.
