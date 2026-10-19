"""Real capture-intake verification from a fabricated WebDriver observation.

The fixed fake timestamps do not mean the website was visited. This suite
exercises the actual library APIs and fail-closed control flags.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.public_capture_live_check import main, verify_capture_and_intake
from scripts.public_selenium_capture import FORM, RESULT, ProbeResult


def sample():
    start = datetime(2026, 10, 19, 5, 0, tzinfo=timezone.utc)
    return ProbeResult(start, start + timedelta(seconds=3), "", "Received!", FORM, RESULT)


def test_original_intake_two_files_and_conservative_status():
    report = verify_capture_and_intake(sample())
    assert report["status"] == "local_evidence_bytes_consistent_review_pending"
    assert report["evidence_file_count"] == report["evidence_files_matching"] == 2
    for flag in ("original_site_behavior_verified", "operator_origin_authenticated",
                 "semantics_independently_reviewed", "user_data_accessed",
                 "generation_authorized", "deployment_authorized"):
        assert report[flag] is False
    captured = Path(report["capture_folder"])
    stored = Path(report["intake_folder"])
    assert sorted(p.name for p in (stored / "captures").iterdir()) == ["selenium_after.txt", "selenium_before.txt"]
    assert json.loads((stored / "capture_intake.json").read_text())["status"] == "pending_manual_evidence_review"
    import shutil
    shutil.rmtree(captured)
    shutil.rmtree(stored)


def test_forged_message_fails_before_creating_success():
    from dataclasses import replace
    with pytest.raises(ValueError, match="inconsistent"):
        verify_capture_and_intake(replace(sample(), after_message="fake"))


def test_no_run_stays_offline_and_no_write(capsys, monkeypatch):
    def no_import(_):
        raise AssertionError("unwanted import")
    assert main([]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["mode"] == "dry_run"
    assert d["browser_started"] is False
    assert d["network_used"] is False
    assert d["files_written"] is False


def test_help_has_explicit_run_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "--run" in capsys.readouterr().out


def test_invalid_flag_exits_before_browser(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--unknown"])
    assert exc.value.code == 2
