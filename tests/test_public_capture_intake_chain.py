"""Offline contract handoff: fake WebDriver capture -> real preexisting intake.

These tests do not visit the source website, establish capture provenance, or
approve code generation. They exercise the actual two module APIs together.
"""
from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.capture_intake import (
    CaptureIntakeManifest, CaptureIntakeRequest, register_captures, verify_captures,
)
from astra_contracts.observation import ObservationBundle
from scripts.public_selenium_capture import FORM, RESULT, ProbeResult, make_review_package


def output_folder() -> Path:
    return Path(tempfile.gettempdir()) / ("astra-selenium-public-" + uuid.uuid4().hex)


@pytest.fixture
def staged_package():
    start = datetime(2026, 10, 19, 4, 15, tzinfo=timezone.utc)
    probe = ProbeResult(
        before_time=start, after_time=start + timedelta(seconds=2),
        before_message="", after_message="Received!",
        first_url=FORM, last_url=RESULT,
    )
    path = output_folder()
    make_review_package(probe, path)
    try:
        bundle = ObservationBundle.model_validate_json(
            (path / "bundle.json").read_text(encoding="utf-8"))
        request = CaptureIntakeRequest.model_validate_json(
            (path / "request.json").read_text(encoding="utf-8"))
        yield path, bundle, request
    finally:
        import shutil
        if path.exists():
            shutil.rmtree(path)


def test_real_intake_register_verify_two_redacted_dom_files(staged_package):
    src, bundle, request = staged_package
    assert bundle.observations[0].certainty.value == "inferred"
    assert len(request.captures) == 2
    before = {p.relative_to(src).as_posix():p.read_bytes()
              for p in src.rglob("*") if p.is_file()}
    with tempfile.TemporaryDirectory(prefix="astra-capture-") as output:
        dst = Path(output)
        manifest = register_captures(bundle, src, request, dst)
        assert isinstance(manifest, CaptureIntakeManifest)
        assert manifest.status == "pending_manual_evidence_review"
        assert manifest.source_bundle_unchanged
        assert not any((
            manifest.original_site_behavior_verified,
            manifest.screenshot_authenticity_verified,
            manifest.user_approval_verified,
            manifest.code_generation_authorized,
            manifest.database_access_authorized,
            manifest.deployment_authorized,
        ))
        assert len(manifest.entries) == 2
        assert {e.evidence.id for e in manifest.entries} == {
            "selenium_before", "selenium_after"}
        verified = verify_captures(bundle, dst)
        assert verified.result == "bytes_match_untrusted"
        assert verified.captured_file_count == verified.bytes_matching == 2
        assert verified.original_behavior_verified is False
        assert verified.capture_authenticity_verified is False
        assert all(x["result"] == "bytes_match_untrusted" for x in verified.findings)
        assert {p.name for p in (dst / "captures").iterdir()} == {
            "selenium_before.txt", "selenium_after.txt"}
        assert all("cookie" not in (dst / "captures" / name).read_text().lower()
                   for name in ("selenium_before.txt", "selenium_after.txt"))
    after = {p.relative_to(src).as_posix():p.read_bytes()
             for p in src.rglob("*") if p.is_file()}
    assert before == after  # original staged capture and observation untouched


def test_same_length_capture_tampering_is_detected(staged_package):
    src, bundle, request = staged_package
    with tempfile.TemporaryDirectory(prefix="astra-capture-") as output:
        dst = Path(output)
        register_captures(bundle, src, request, dst)
        path = dst / "captures" / "selenium_after.txt"
        raw = path.read_bytes()
        assert b"Received!" in raw
        path.write_bytes(raw.replace(b"Received!", b"Replaced!"))  # same bytes
        assert verify_captures(bundle, dst).result == "evidence_incomplete"
        assert {x["result"] for x in verify_captures(bundle, dst).findings} == {
            "bytes_match_untrusted", "hash_mismatch"}


def test_stale_source_bundle_refused_before_writing(staged_package):
    src, bundle, request = staged_package
    edited = bundle.model_copy(update={"scope":"changed"})
    with tempfile.TemporaryDirectory(prefix="astra-capture-") as output:
        path = Path(output)
        with pytest.raises(ValueError, match="stale"):
            register_captures(edited, src, request, path)
        assert list(path.iterdir()) == []


def test_wrong_capture_observation_link_refused_before_writing(staged_package):
    src, bundle, request = staged_package
    edited = request.model_dump(mode="json")
    edited["captures"][0]["observation_ids"] = ["wrong_observation"]
    wrong = CaptureIntakeRequest.model_validate(edited)
    with tempfile.TemporaryDirectory(prefix="astra-capture-") as output:
        path = Path(output)
        with pytest.raises(ValueError, match="unknown observation"):
            register_captures(bundle, src, wrong, path)
        assert list(path.iterdir()) == []


def test_forged_intake_approval_cannot_be_imported(staged_package):
    src, bundle, request = staged_package
    with tempfile.TemporaryDirectory(prefix="astra-capture-") as output:
        manifest = register_captures(bundle, src, request, Path(output))
        forged = manifest.model_dump(mode="json")
        forged["original_site_behavior_verified"] = True
        with pytest.raises(ValidationError):
            CaptureIntakeManifest.model_validate(forged)
