# ASTRA p4 — Manual action trace → draft spec → fictional app smoke (v0.1)

## Bounded first end-to-end connection

A **single CLI command** takes a *locally supplied*, sanitized manual-test JSON action record bound to one unapproved `ObservationBundle`, confirms that the reported action and shared before/after UI state match the original bundle, drafts a `FunctionalSpecDraft`, recomputes a **fictional** schema mapping report, creates the still-**blocked** generation contract, delegates to the fixed standalone synthetic FastAPI/SQLite app generator, and runs independent `SyntheticAcceptanceReport` tests. Finally it writes a non-authorizing `data/manual_pipeline_report.json` beside the eight previous generated preview files.

**What it does not do:** observe/visit the actual website; authenticate screenshots/user claims; verify a click was actually performed; reverse-engineer source code/formulas; generate arbitrary business logic from the captured action; connect a real customer DB/API; grant codegen, owner-schema, source access or deployment permission; run Vercel/GitHub Actions or browser E2E. The generated app uses **fictional fixture rows and a fixed code template**; its functioning does not prove the source UI works. The example's `certainty='observed'` is an *unverified operator label*, not independent confirmation.

## Inputs and restrictions

- Exactly one source observation and exactly one evidence record for v0.1. Evidence must be a `manual_test` **JSON** file referenced by the observation; no inferred/unknown source claim is allowed for the *reported-action draft*.
- The trace file must contain `provenance='unverified_operator_supplied_manual_test'`, matching observation/evidence IDs, exact declared action, identical typed JSON `before`/`after` states, and at least one changed shared key. All approval and authenticity fields are literal `false`. This is **consistency**, not a proof of original-site behavior.
- File input is read by `evidence_integrity._read_capture`, rejecting unsafe/traversal/symlink paths, oversized or sensitive-marked text and malformed JSON.
- Schema declaration **must** say `source_kind='synthetic_fixture'`; the codegen request must be the existing `contract_only`, isolated FastAPI/SQLite request. Mapping report and blocked contract are derived in memory from current inputs — never accepted from a caller. Destination must be an existing **empty** `astra-synth-*` system-temporary directory, directly under the OS temp root.
- Production generation approval stays `blocked_pending_review`; all actual-source, identity, DB, deployment and formula verification fields remain literal `false`.

## Reproducible synthetic-only example

From repository root, with Python dependencies installed:

```bash
OUT=$(mktemp -d /tmp/astra-synth-manual-XXXXXXXX)
python -m astra_contracts.manual_trace_pipeline \
  fixtures/synthetic_manual_filter_observation_20261019.json \
  fixtures \
  fixtures/synthetic_manual_filter_schema_20261019.json \
  fixtures/synthetic_generation_request_20261018.json \
  fixtures/synthetic_demo_catalog_20261018.json \
  "$OUT"
python -m astra_contracts.synthetic_acceptance "$OUT"
python -m pytest -q tests/test_*.py
```

On Windows, create a fresh empty folder named `astra-synth-...` directly within Python's `tempfile.gettempdir()` and use that full path as the sixth argument. No shell, network, browser or GitHub Actions integration is needed for the CLI.

Sample trace explicitly says `Fictional example: choose a different category`, with invented before/after values (`ALL` → `ART`, 4 → 2). **That source state is not used as sample database content**; it is only associated with a synthetic smoke filter route from the separate fictional product fixture. The suite verifies generated health/list/filter/search/detail/404/422/SQLite-persistence and source-template integrity.

## Local verification / failures

2026-10-19 KST, Python 3.13: prior **349** tests + **24** new end-to-end/negative assertions = **373/373 PASS**, `compileall` PASS. New unit tests cover stale/mismatched action/ID/state, JSON boolean-vs-number equality, unknown/inferred observations, missing/symlink/broken evidence, forged approval, unsafe/nonempty output, wrong stack, real-owned schema rejection, incompatible old mapping, source immutability, persisted report and independent repeated synthetic acceptance. One initial test asserted a lowercase error substring against the generator's uppercase `EMPTY` error; test wording corrected and full suite rerun. One existing httpx deprecation warning unrelated to this unit.

Manual-action run produced 8 generator files plus one additional `data/manual_pipeline_report.json`, with 12 synthetic acceptance assertions PASS; the actual acceptance check creates a disposable SQLite database and does not connect any customer data. No real original URL/browser, GUI tests, new human captures, unapproved system mutations or deployment. `main` and previously existing apps remain unchanged.

## Next actual product steps

Extend beyond one unverified manual action; support an explicitly authorized original-site demonstration with independent corroboration and *real* user-controlled schema semantics under a separately documented approval process. Then make the implementation feature adapter replay actual acceptance assertions rather than a hard-coded unrelated fictional demo. Until these milestones, do not advertise a completed general URL→working-user-DB application generator.
