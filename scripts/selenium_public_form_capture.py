"""Explicit opt-in, one-site public demo browser observation.

No arguments: print the approved dry-run plan. Never automatically bypass blocked
browsers, log in, touch customer data, or visit arbitrary URLs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

PUBLIC_URL = "https://www.selenium.dev/selenium/web/web-form.html"
DEMO_INPUT = "Astra public demo"
RESULT_TEXT = "Received!"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _capture(driver, output_dir: Path) -> dict:
    """Use with a browser only after explicit opt-in. Driver is injected for unit testing."""
    driver.get(PUBLIC_URL)
    if driver.current_url.split("?", 1)[0].rstrip("/") != PUBLIC_URL:
        raise RuntimeError("unexpected original page redirect")
    before_file = output_dir / "before.png"
    after_file = output_dir / "after.png"
    if not driver.save_screenshot(str(before_file)):
        raise RuntimeError("failed before screenshot")
    before_time = _utc_now()
    # The selectors and response are from the official Selenium tutorial, not inferred.
    text_box = driver.find_element("name", "my-text")
    text_box.send_keys(DEMO_INPUT)
    button = driver.find_element("css selector", "button")
    button.click()
    message = driver.find_element("id", "message").text
    if message != RESULT_TEXT:
        raise RuntimeError(f"submitted state mismatch: {message!r}")
    after_time = _utc_now()
    after_url = driver.current_url
    if urlsplit(after_url).scheme != "https" or urlsplit(after_url).hostname != "www.selenium.dev":
        raise RuntimeError("after-submit redirect left allowlisted public demo host")
    if not driver.save_screenshot(str(after_file)):
        raise RuntimeError("failed after screenshot")
    result = {
        "version": "0.1", "reference_url": PUBLIC_URL,
        "reported_after_url": after_url,
        "before_timestamp_utc": before_time, "after_timestamp_utc": after_time,
        "operator_action": "type fictional demo text into name=my-text and click Submit",
        "result_message_observed": message,
        "before_sha256": hashlib.sha256(before_file.read_bytes()).hexdigest(),
        "after_sha256": hashlib.sha256(after_file.read_bytes()).hexdigest(),
        "browser_interaction_executed": True,
        "site_test_smoke_passed": True,
        "external_origin_independently_authenticated": False,
        "human_review_completed": False,
        "customer_db_access_authorized": False,
        "code_generation_authorized": False,
        "deployment_authorized": False,
        "mapped_ui_controls_enabled": False,
    }
    (output_dir / "capture_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv=None, driver_factory=None):
    parser = argparse.ArgumentParser(description="Opt-in Selenium public form smoke; dry-run by default")
    parser.add_argument("--run-public-demo", action="store_true")
    args = parser.parse_args(argv)
    if not args.run_public_demo:
        print(json.dumps({"mode":"dry_run", "target":PUBLIC_URL,
                          "action":"type fixed fictional text, submit, screenshot before/after",
                          "network_used":False,"browser_launched":False}, indent=2))
        return 0
    if driver_factory is None:
        from selenium import webdriver
        driver_factory = webdriver.Chrome
    directory = Path(tempfile.mkdtemp(prefix="astra-public-proof-"))
    driver = None
    try:
        driver = driver_factory()
        result = _capture(driver, directory)
        print(json.dumps({"capture_dir":str(directory),"report":result},indent=2))
        return 0
    except Exception as exc:
        # Do not silently retry forbidden browser navigation or override restrictions.
        print(json.dumps({"status":"failed_no_retry","capture_dir":str(directory),
                          "error":f"{type(exc).__name__}: {exc}"},indent=2))
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
