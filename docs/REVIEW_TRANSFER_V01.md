# ASTRA p4 — offline review opinion transfer v0.1 (one bounded unit)

## Purpose

Move **unverified reviewer opinions** between local ASTRA review sessions without implying authority or access. The portable JSON file has version `0.1`, the **current ReviewPacket fingerprint**, canonical record SHA-256, and the complete `ReviewRecord`. It must never contain a live access token, customer credentials or an approval. This is not an authenticated signature, tamper-proof attestation or reviewer identity verification: **anyone can recompute a SHA-256 on a forged, structurally valid opinion**.

An attempted export/import rebuilds allowed opinion records against the **currently validated review packet** via `record_opinions()`. It rejects different/old packet hashes, altered counts, missing/duplicate/extra items, forged flags, invalid evidence references, invented approvals, and declarations that unknown behavior or incompatible mappings are supported. All authorization flags are immutable `false`, including identity verification, production code generation, DB access and deployment.

## Files and API

- `astra_contracts/review_transfer.py`: `export_bundle(packet, record)` returns a deterministic, read-only JSON-compatible `ReviewTransferBundle`; `import_bundle(packet, bytes)` validates size, format, SHA and original `ReviewRecord` business constraints; **returns only a record**, never grants permissions.
- `astra_contracts/review_ui.py`: `GET /api/export/{record_id}` downloads the JSON bundle. `POST /api/import` accepts `application/json` with the active ephemeral local session token and creates one new unique record JSON inside the already guarded temporary review folder. Both routes refuse invalid tokens/origin and outside-folder paths.
- `astra_contracts/review_ui.js`, `.html`: download button and local file selector/import button; selected JSON stays local except being sent to `127.0.0.1` review server. The UI labels imported opinions unverified and unapproved.
- CLI read-only check: `python -m astra_contracts.review_transfer <current_review_packet.json> <downloaded_opinion_bundle.json>` returns JSON `valid_for_current_packet`, `authenticated:false`, `approved:false`; it **does not import** the record into any app or modify files.

## Security and provenance

- JSON has strict Pydantic v2 schemas (`extra='forbid'`) and a 64 KiB transport cap.
- No API requests, authentication/identity attestation, production source changes, database connections, secrets, migrations, deployment or remote GitHub Actions.
- Same-origin host/origin check and per-instance randomly generated review token are local CSRF mitigations **only**; they are not proof of user identity or consent.
- Exported file is a **claimed opinion**, not a verified approval. Altering the file and recalculating its hash cannot make it authoritative. Truly verified approval and owner-schema authorization would require an independent process.
- Reference UI behavior and any customer-owned DB/API are still unverified; Japanese nail case and schema fields are synthetic/archived samples.

## Verification

From repository root:

```bash
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
node --check astra_contracts/review_ui.js
```

The new test suite covers valid roundtrips, exported SHA, changed packet, corrupted or forged record, regenerated hashes on internally contradictory files, missing/extra fields, size limits, local-session access checks, actual HTTP import/export, and absence of authorization. Browser GUI click testing was previously **blocked by policy** and is not claimed as tested here. Successful test cases are **local synthetic fixtures only**.

## Next unit

Either run **manual browser acceptance in an eligible environment** or implement an evidence acquisition/reverification flow from an explicitly authorized sample URL; continue to leave real-source formulas, schema integration and production code generation behind verified human approval gates.
