"""Synthetic driver tests of public OWID chart->table capture; no live browser here."""
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest

from scripts.public_owid_dashboard_probe import (
    SOURCE, TABLE, capture_and_verify, guard_url, main,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRVsAAAAASUVORK5CYII="
)


class Control:
    def __init__(self, driver):
        self.driver = driver
    def is_displayed(self):
        return True
    def is_enabled(self):
        return True
    def click(self):
        self.driver.clicked = True
        self.driver.current_url = TABLE


class FakeDriver:
    current_url = SOURCE
    clicked = False
    def __init__(self, rows=2, control=True):
        self.rows = rows
        self.control = control
        self.clicked = False
        self.current_url = SOURCE
    def get(self, url):
        assert url == SOURCE
        self.current_url = url
    def save_screenshot(self, filename):
        Path(filename).write_bytes(PNG)
        return True
    def find_elements(self, mode, selector):
        if mode == "xpath":
            return [Control(self)] if self.control else []
        if mode == "css selector" and selector == "table tbody tr":
            return [object()] * (self.rows if self.clicked else 0)
        raise AssertionError("unexpected selector")


def wait(d):
    assert d.clicked


def test_safe_allowlisted_dashboard_urls():
    guard_url(SOURCE)
    guard_url(TABLE)


@pytest.mark.parametrize("url", [
    "http://ourworldindata.org/grapher/life-expectancy?tab=table",
    "https://other.example/grapher/life-expectancy?tab=table",
    "https://ourworldindata.org/grapher/other?tab=table",
    "https://ourworldindata.org/grapher/life-expectancy?access_token=secret",
    "https://ourworldindata.org/grapher/life-expectancy#secret",
    "https://name:pass@ourworldindata.org/grapher/life-expectancy",
    "https://ourworldindata.org:8443/grapher/life-expectancy",
])
def test_unsafe_urls_fail_closed(url):
    with pytest.raises(ValueError, match="unsafe URL|unexpected"):
        guard_url(url)


def test_actual_capture_intake_contract_stays_unapproved():
    data = capture_and_verify(FakeDriver(), wait)
    try:
        assert data["status"] == "public_dashboard_capture_review_pending"
        assert data["matched_screenshots"] == 2
        assert data["after_table_rows"] == 2 and data["before_table_rows"] == 0
        for key in ("original_site_behavior_verified", "customer_schema_connected",
                    "generation_authorized", "deployment_authorized"):
            assert data[key] is False
        root = Path(data["capture_dir"])
        assert (root / "captures/before.png").read_bytes() == PNG
        assert (root / "captures/after.png").read_bytes() == PNG
        report = json.loads((root / "intake_manifest.json").read_text())
        assert report["status"] == "pending_manual_evidence_review"
        assert {e["evidence"]["id"] for e in report["entries"]} == {"before", "after"}
        assert report["original_site_behavior_verified"] is False
    finally:
        shutil.rmtree(data["capture_dir"])
        shutil.rmtree(data["intake_dir"])


def test_missing_table_control_fails_no_false_success():
    with pytest.raises(ValueError, match="Table control"):
        capture_and_verify(FakeDriver(control=False), wait)


def test_no_rows_after_click_fails():
    with pytest.raises(ValueError, match="row count"):
        capture_and_verify(FakeDriver(rows=0), wait)


def test_default_run_offline(capsys):
    assert main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["browser"] is False
    assert report["network"] is False
    assert report["files_written"] is False
