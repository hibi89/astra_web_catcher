"""Bounded real-data dashboard observation: public OWID chart -> table toggle.

No account, arbitrary URLs, private API, owner DB or code generation.
Default invocation only emits an offline plan. A live run requires --run and
uses one publicly available Our World in Data grapher page.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

from astra_contracts.capture_intake import (
    CaptureIntakeRequest, register_captures, verify_captures,
)
from astra_contracts.generation_contract import fingerprint
from astra_contracts.observation import ObservationBundle

SOURCE = "https://ourworldindata.org/grapher/life-expectancy?tab=chart"
TABLE = "https://ourworldindata.org/grapher/life-expectancy?tab=table"
ACTION = "Select the Table view on a public life-expectancy dashboard"
TARGET_HOST = "ourworldindata.org"
TARGET_PATH = "/grapher/life-expectancy"


def guard_url(value: str) -> None:
    parts = urlsplit(value)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    if (parts.scheme != "https" or parts.hostname != TARGET_HOST
            or parts.port is not None or parts.username is not None
            or parts.password is not None or parts.path != TARGET_PATH
            or parts.fragment or len(parts.query) > 400
            or any(k.lower() in {"token", "password", "access_token", "authorization", "key"}
                   for k, _ in pairs)):
        raise ValueError("unexpected dashboard navigation or unsafe URL")


def click_table(driver, wait) -> tuple[datetime, datetime, int, int]:
    """Navigate to an actual public chart and click the visible Table control."""
    driver.get(SOURCE)
    guard_url(driver.current_url)
    if driver.current_url.split("?")[0] != SOURCE.split("?")[0]:
        raise ValueError("source page path changed")
    before_count = len(driver.find_elements("css selector", "table tbody tr"))
    before = datetime.now(timezone.utc)

    # Use visible user controls, not JavaScript state mutation or direct URL swap.
    candidates = driver.find_elements(
        "xpath",
        "//button[normalize-space()='Table'] | //a[normalize-space()='Table'] "
        "| //*[@role='tab' and normalize-space()='Table']"
    )
    choices = [c for c in candidates if c.is_displayed() and c.is_enabled()]
    if not choices:
        raise ValueError("visible Table control not found; no click or evidence claim")
    choices[0].click()
    wait(driver)
    guard_url(driver.current_url)
    after_count = len(driver.find_elements("css selector", "table tbody tr"))
    if after_count < 1:
        raise ValueError("real table rows not visible after clicking Table")
    after = datetime.now(timezone.utc)
    return before, after, before_count, after_count


def capture_and_verify(driver, wait) -> dict:
    """Evidence includes two real browser PNG screenshots and no copied page source."""
    root = Path(tempfile.gettempdir()) / ("astra-owid-" + uuid.uuid4().hex)
    # Store only fixed-reference screenshot evidence. No cookies or raw HTML.
    driver.get(SOURCE)
    guard_url(driver.current_url)
    root.mkdir(mode=0o700)
    (root / "captures").mkdir(mode=0o700)
    before = datetime.now(timezone.utc)
    if not driver.save_screenshot(str(root / "captures" / "before.png")):
        raise ValueError("before screenshot failed")
    # Reuse the real public page, without a second navigation.
    before_count = len(driver.find_elements("css selector", "table tbody tr"))
    candidates = driver.find_elements(
        "xpath", "//button[normalize-space()='Table'] | //a[normalize-space()='Table'] "
                 "| //*[@role='tab' and normalize-space()='Table']"
    )
    choices = [c for c in candidates if c.is_displayed() and c.is_enabled()]
    if not choices:
        raise ValueError("visible Table control not found")
    choices[0].click()
    wait(driver)
    guard_url(driver.current_url)
    after_count = len(driver.find_elements("css selector", "table tbody tr"))
    if after_count <= before_count or after_count < 1:
        raise ValueError("row count failed to rise after Table click")
    after = datetime.now(timezone.utc)
    if not driver.save_screenshot(str(root / "captures" / "after.png")):
        raise ValueError("after screenshot failed")
    bundle = ObservationBundle.model_validate({
        "schema_version": "1.0", "site_url": SOURCE,
        "scope": "Public OWID chart/table observation; actual DOM mechanics not independently reviewed",
        "recorded_at": after.isoformat(), "evidence": [],
        "observations": [{
            "id": "public_table_view", "feature": "list",
            "title": "Chart view changes to visible tabular rows",
            "claim": "Runner clicked visible Table control; semantics and source authenticity require review.",
            "certainty": "inferred", "evidence_ids": [], "action": ACTION,
            "before": {"visible_table_rows": before_count, "view": "chart"},
            "after": {"visible_table_rows": after_count, "view": "table"},
        }]
    })
    captures = [
        {"evidence": {
            "id": suffix, "kind": "screenshot",
            "source_ref": "captures/" + suffix + ".png",
            "captured_at": stamp.isoformat(),
            "notes": "Public data site PNG; human review pending"},
            "observation_ids": ["public_table_view"]}
        for suffix, stamp in (("before", before), ("after", after))
    ]
    request = CaptureIntakeRequest.model_validate({
        "version": "0.1", "source_kind": "manually_supplied_local_files",
        "observation_sha256": fingerprint(bundle), "captures": captures
    })
    intake = Path(tempfile.gettempdir()) / ("astra-capture-" + uuid.uuid4().hex)
    intake.mkdir(mode=0o700)
    manifest = register_captures(bundle, root, request, intake)
    result = verify_captures(bundle, intake)
    if (result.result != "bytes_match_untrusted" or result.bytes_matching != 2
            or result.captured_file_count != 2 or manifest.original_site_behavior_verified):
        raise ValueError("screenshot intake byte validation failed")
    (root / "bundle.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    (root / "request.json").write_text(request.model_dump_json(indent=2), encoding="utf-8")
    (root / "intake_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return {
        "status": "public_dashboard_capture_review_pending",
        "public_source": SOURCE, "action": ACTION,
        "before_table_rows": before_count, "after_table_rows": after_count,
        "capture_dir": str(root),
        "intake_dir": str(intake),
        "matched_screenshots": result.bytes_matching,
        "original_site_behavior_verified": False,
        "customer_schema_connected": False,
        "generation_authorized": False,
        "deployment_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Public interactive dashboard screenshot test")
    parser.add_argument("--run", action="store_true", help="explicitly visit a public dashboard and click Table")
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps({"mode": "dry_run", "source": SOURCE,
                          "network": False, "browser": False, "files_written": False}))
        return 0
    driver = None
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(30)
        driver.get(SOURCE)
        WebDriverWait(driver, 20).until(
            lambda d: any(c.is_displayed() for c in d.find_elements(
                "xpath", "//button[normalize-space()='Table'] | //a[normalize-space()='Table'] "
                         "| //*[@role='tab' and normalize-space()='Table']")))
        def wait(d):
            return WebDriverWait(d, 15).until(
                lambda x: len(x.find_elements("css selector", "table tbody tr")) > 0)
        result = capture_and_verify(driver, wait)
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.quit()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
