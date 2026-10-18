# ASTRA p4 — Local evidence-capture intake v0.1

## What it does

A bounded, **offline** intake for operator-provided screenshot, sanitized DOM text, manual test, user demonstration, or sanitized-network evidence files. It produces an immutable-ish **proposed association** between capture IDs and previously known observation IDs. Source `ObservationBundle` is **never modified**; the evidence copy and manifest are written exclusively to a newly created, empty `astra-capture-*` folder directly inside the OS temporary directory.

This is **not** automatic website screenshot capture, semantic OCR/image understanding, original-site causality verification, user identity verification, consent, permission to operate any DB/API, general code generation, or deployment. An evidence digest proves only bytes match the intake manifest that the operator supplied/created. Approval and behavior-proof flags are always `false`, including for PNGs and screenshots.

## Input contract

- Original `ObservationBundle` v1 with observations and evidence already declared. It may include unknown/inferred claims; intake **never upgrades their certainty**, computes formulas, or attaches evidence to the original bundle.
- `CaptureIntakeRequest` v0.1 with exact bundle SHA-256, `source_kind=manually_supplied_local_files` (a label, **not** user authentication), and up to 20 `captures`. Each has a new `Evidence` object and 1–20 existing observation IDs. Archived secondary reports cannot be represented as newly captured evidence. Reused evidence IDs, unknown observations, duplicate input paths and malformed timestamps fail validation.
- Local `source_root` directory holding the explicitly selected files. The existing `_read_capture()` enforces relative paths, fixed evidence kind/extension, no symlinks, no credential-like text patterns, basic image signature, max 10 MiB per file. These tests are not full image validation or malware/secret detection: **manually sanitize any screenshots before intake**.
- A caller-created **empty**, directly nested OS temporary `astra-capture-*` output folder. No copying to the GitHub repo, no overwriting unrelated files, no destructive cleanup.

## Outputs

`captures/<safe_evidence_id>.<extension>` containing byte-for-byte copied source captures, plus `capture_intake.json` with version, original observation hash, request hash, evidence metadata, exact observation references, file digest/size and explicit pending-review/non-approval status.

`verify` recomputes checks against the unchanged original bundle, validates referenced observation IDs and stored capture paths, and reports `bytes_match_untrusted`, `missing_file`, `size_mismatch`, `hash_mismatch` or `rejected_unsafe_file`. A changed or stale source bundle fails verification; output manifest is capped at 256 KiB. Stored manifest and files can be jointly altered by someone with folder access, so this is a consistency check, **not** a digital signature, trusted timestamp or audit-grade provenance authority.

## Reproducible fictional example from repository root

```sh
OUT=$(mktemp -d /tmp/astra-capture-demo-XXXXXXXX)
python -m astra_contracts.capture_intake register \
  fixtures/synthetic_capture_observation_20261018.json \
  fixtures \
  fixtures/synthetic_capture_intake_request_20261018.json \
  "$OUT"
python -m astra_contracts.capture_intake verify \
  fixtures/synthetic_capture_observation_20261018.json "$OUT"
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

**WARNING:** `fixtures/evidence/synthetic_dom_capture_20261018.txt` is fabricated text; `https://example.org/...` in the sample is a placeholder, never accessed by this tool. No actual capture of the historical nail site has been supplied. The sample's filter observation deliberately remains `inferred`.

## Tested scope (2026-10-18 KST)

Existing 270 plus 32 new tests = **302/302 PASS**, with one preexisting httpx deprecation warning; Python compileall PASS; real fixture CLI register/verify produces 1 pending synthetic DOM entry with matching bytes. Tests include accidental overwrite prevention, batch preflight without partial writes on invalid source, duplicate IDs/paths, wrong source-bundle SHA, unknown observation associations, unsafe traversal/symlinks, unauthorized flag spoofing, forged output association, tampered file hash and oversized manifest. No GitHub Actions, browser automation, real customer API/DB, or deployment executed.

## Next bounded task

Human supplies an authorized, sanitized **real** screenshot/DOM plus its own observation record, then uses the same safe intake and separately reviews what is directly visible. A later independent human-reviewed process may turn a verified visual fact into a candidate spec; **it must not silently upgrade claims from this intake alone**. Until then, no general URL→production-app milestone is complete.
