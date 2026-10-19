"""Explicit public Selenium browser action + original ASTRA intake verification.

Default is dry-run. --run launches a compatible locally available Chrome to
interact once with *only* Selenium's published public test form. This tool does
not authenticate origin/author, grant review approval, or access customer data.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from pathlib import Path

from astra_contracts.capture_intake import (
    CaptureIntakeRequest, register_captures, verify_captures,
)
from astra_contracts.observation import ObservationBundle
from scripts.public_selenium_capture import FORM, ProbeResult, capture_fixed_flow, make_review_package


def verify_capture_and_intake(probe: ProbeResult) -> dict:
    """Call the actual capture-intake APIs after a bounded browser observation.

    Hash/pair checks establish local byte-consistency only. Never mark the
    source website's real behavior independently verified by this function.
    """
    temp = Path(tempfile.gettempdir())
    capture_root = temp / ("astra-selenium-public-" + uuid.uuid4().hex)
    capture = make_review_package(probe, capture_root)
    bundle = ObservationBundle.model_validate_json(
        (capture_root / "bundle.json").read_text(encoding="utf-8"))
    request = CaptureIntakeRequest.model_validate_json(
        (capture_root / "request.json").read_text(encoding="utf-8"))
    intake_root = temp / ("astra-capture-" + uuid.uuid4().hex)
    intake_root.mkdir(mode=0o700)
    manifest = register_captures(bundle, capture_root, request, intake_root)
    checked = verify_captures(bundle, intake_root)
    if (checked.result != "bytes_match_untrusted" or checked.bytes_matching != 2
            or checked.captured_file_count != 2
            or len(manifest.entries) != 2
            or manifest.original_site_behavior_verified
            or checked.original_behavior_verified
            or checked.capture_authenticity_verified):
        raise ValueError("offline evidence integrity did not pass: no success report")
    return {
        "status": "local_evidence_bytes_consistent_review_pending",
        "source_reference_url": FORM,
        "evidence_file_count": checked.captured_file_count,
        "evidence_files_matching": checked.bytes_matching,
        "capture_folder": str(capture_root),
        "intake_folder": str(intake_root),
        "capture_sha256": capture["observation_sha256"],
        "original_site_behavior_verified": False,
        "operator_origin_authenticated": False,
        "semantics_independently_reviewed": False,
        "user_data_accessed": False,
        "generation_authorized": False,
        "deployment_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="One public Selenium demo click + original ASTRA evidence intake")
    parser.add_argument("--run", action="store_true", help="explicitly start local Chrome and use the published public Selenium demo")
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps({"mode": "dry_run", "source": FORM,
                          "browser_started": False, "network_used": False,
                          "files_written": False}, indent=2))
        return 0
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        print("FAIL: install selenium before an explicit --run", file=sys.stderr)
        return 2
    driver = None
    try:
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(20)
        def wait_for_received(session):
            return WebDriverWait(session, 10).until(
                lambda d: d.find_element("id", "message").text.strip() == "Received!")
        observation = capture_fixed_flow(driver, wait_for_received)
        result = verify_capture_and_intake(observation)
    except Exception as exc:
        print(f"FAIL: public Selenium live check or intake verification failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception as exc:
                print(f"WARNING: could not close Chrome cleanly: {type(exc).__name__}", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
