# ASTRA p4 — OWID chart/table review-only mechanism skill

**2026-10-19 KST · bounded unit · no customer DB / deployment**

## Decision and alternative comparison

The actual Chrome proof shows the public OWID life-expectancy chart switching to Table mode. It demonstrates a reusable **proposed presentation mechanism**, not the original algorithm or a verified data-model equivalence.

| Design | Cost / performance / maintenance | Decision |
| --- | --- | --- |
| Static Markdown / JSON recipe | Lowest cost, but no cryptographic evidence integrity or fail-closed validation | Rejected |
| Python standard-library pinned ZIP verifier and guarded skill report | Fast/offline, low dependency cost, testable screenshot and review boundaries | Selected |

## Source proof and fixed evidence

- GitHub Actions run: https://github.com/hibi89/astra_web_catcher/actions/runs/39211418515
- Artifact ID: 12168150702 (https://github.com/hibi89/astra_web_catcher/actions/runs/39211418515/artifacts/12168150702)
- ZIP size: 274126 bytes
- ZIP SHA-256: 6ad5f561b78271be7da3b4efb8e61fcc1a6c269b4ebf8a26e1b32c23b81717e6
- Observation ID: public_table_view, certainty=inferred; original bundle does not promote certainty.
- Screenshot before: captures/before.png, 159304 bytes, SHA-256 d94cf65cb9850f2546b078759214414b70ad7f277e5200970d76489fe6df8c60
- Screenshot after: captures/after.png, 122367 bytes, SHA-256 4abdc085d07cfa0397e3a626eab23974d28107becb680dfdcdf7f1ab60a5e6dc
- Live reported transition: chart, 0 DOM table rows → click visible Table → table, 265 DOM rows.
- Capture timestamps: 2026-10-19T06:42:28.513725Z → 2026-10-19T06:42:29.202048Z.

## Implemented files and commands

- astra_contracts/chart_table_transition_skill.py: pinned-archive verifier and review-only skill output.
- tests/test_chart_table_transition_skill.py: fail-closed synthetic tests for altered screenshots, forged approvals, view-state tampering, symlinks, extra files and mistaken provenance.

Run these from the repository root:

    python -m astra_contracts.chart_table_transition_skill
    python -m astra_contracts.chart_table_transition_skill --archive /path/to/p4-owid-evidence.zip
    python -m pytest -q tests/test_chart_table_transition_skill.py

The no-argument invocation prints dry-run JSON only. The archive invocation uses only local bytes, without network, browser, file writes, owner DB access or code generation. SHA-256 of the full ZIP, screenshot SHA/size, manifest and request fingerprints, evidence IDs, timestamps, original claim levels and approval-false flags must match exactly.

**Verified for this bounded unit:** 10/10 local pytest PASS on Python 3.13; independently downloaded actual GitHub ZIP passed the new verifier; the exact two committed Python blobs were read back and matched the local files by Git blob SHA.

**Not verified:** whole-repository regression suite, arbitrary URLs, original OWID internals, customer schemas, Windows UI, production app operation, deployments.

## Review-only mechanism contract

- Skill: chart_table_mode_switch; trigger: click_visible_table_control.
- Proposed adapter: show chart/table as two representations of a declared, owner-approved dataset.
- Unknowns: original source/backend implementation, sorting, equivalent processed data, formulas and aggregation semantics.
- Required owned fields: entity identifier, time period, numeric measure, aggregation semantics.
- The available sample categories/products/companies/job_postings DDL is incompatible with the target metric. **Zero approved owner semantic bindings.**
- Source claim is **inferred** and screenshot authenticity is not independently certified merely by byte validation.
- All owner DB access, generation, approval and deployment flags remain false; GenerationContract=blocked_pending_review.

Artifact retention ends approximately **2026-10-22 15:42 KST**. After expiry the fixed hashes remain, but the ZIP itself must have been retained elsewhere to reproduce its byte verification. This document is not a substitute for actual archived evidence.

**Next bounded unit:** with a declared synthetic time-series schema, add an offline schema-to-mode-switch review adapter that surfaces missing semantic fields without authorizing generation. For real customer data, obtain separate explicit scope/approval and use disposable storage first. Preserve protected main and existing demos.
