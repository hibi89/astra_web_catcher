# ASTRA p4 — Local evidence-file integrity verification v0.1

**Scope:** A read-only offline step between an observation bundle and a human reviewer. It verifies whether locally stored evidence files have the same bytes as a self-declared snapshot bound to an exact `ObservationBundle`. It **does not** authenticate a screenshot's origin, prove a site behaved as described, derive metric formulas, grant access, verify identity/consent, or activate production code generation.

## Why this unit

Earlier research had an archived report but no original screenshot file or click trace available in the ASTRA repository. This tool distinguishes a real file whose bytes can be checked from merely referencing a filename. It avoids retrying a known administratively blocked browser/Playwright environment or fetching third-party URLs. Files are not uploaded, copied or changed by either CLI command.

## Inputs and outputs

- `ObservationBundle` v1 includes evidence IDs, relative source references, evidence kind and timestamps, and observations that cite those IDs. This remains the canonical source metadata.
- `snapshot` reads only referenced local files under an operator-supplied directory, validates path/extension/header/text safety, then prints `EvidenceFileManifest` v0.1 JSON with exact observation SHA-256, file IDs/types/references, file size and SHA-256 digest. Save stdout explicitly if needed. **Snapshot is user-declared, untrusted metadata; it is not a signature.**
- `verify` validates an existing manifest against the same observation, checks each current local file, and prints `EvidenceFileAudit` v0.1 with `bytes_match_untrusted`, `missing_file`, `size_mismatch`, `hash_mismatch`, or `rejected_unsafe_file` findings. The result is only an integrity check. False flags for actual capture verification, original behavior, formulas, reviewer identity and approval are enforced by strict models.

## Commands from the repo root

```sh
python -m astra_contracts.evidence_integrity snapshot fixtures/jp_nail_brand_filter_observation_20261018.json .
python -m astra_contracts.evidence_integrity verify fixtures/jp_nail_brand_filter_observation_20261018.json . fixtures/jp_nail_evidence_file_snapshot_20261018.json
python -m pytest -q tests/test_*.py
python -m compileall -q astra_contracts tests
```

Historical case result: one archived report (`evidence/jp_nail_brand_filter_source_20261018.md`) matches the self-declared byte digest; **zero actual captured screenshots have been authenticated or verified**, no browser click trace has been replayed. The matching file was already in the repository; it is not a newly obtained original-site proof.

## Safety contract

Only local relative paths, no URL or credential query, hidden/traversal components, or symlinks; cap 10 MiB per file; kind-specific extensions for image, text and sanitized JSON; check PNG/JPEG/WebP magic headers and basic sensitive text markers. No network request, no database, no file writes, no content copying, no source inference. This basic check cannot detect every secret, falsely asserted capture or spoofed/both-changed manifests. If sensitive source material is present, sanitize and review it **before** running ASTRA. Only separately authorized, user-supplied evidence should be processed. Content hashing is not a provenance authority.

## Verified scope (2026-10-18)

Local Python 3.13: **270/270 pytest PASS** (237 previous plus 33 new, including parameterized adversarial cases), `compileall` PASS, snapshot JSON deterministic and CLI verify PASS. GUI browser/actual source behavior not tested, GitHub Actions not used. Source: `astra_contracts/evidence_integrity.py`, `tests/test_evidence_integrity.py`, `fixtures/jp_nail_evidence_file_snapshot_20261018.json`.

## Next unit

Supply an explicitly authorized **new** manually captured screenshot or sanitized DOM file plus observation bundle, then validate actual file/reference linkage and review what is directly visible before permitting any semantic upgrades. Do not equate hashes with site truth, enable customer DB integration or production deployment without separate authorization. Existing `GenerationContract` must remain blocked.
