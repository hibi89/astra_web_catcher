"""Injected fake driver tests only; no real public browser is launched in CI."""
import importlib.util
import json
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "selenium_public_form_capture.py"
spec = importlib.util.spec_from_file_location("selenium_capture_runner", RUNNER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Element:
    def __init__(self, value=""):
        self.text=value
        self.typed=""
        self.clicked=False
    def send_keys(self, value):
        self.typed += value
    def click(self):
        self.clicked=True


class FakeDriver:
    def __init__(self, wrong_message=False, wrong_redirect=False, fail_image=False, redirect_after=False):
        self.url=module.PUBLIC_URL
        self.wrong_message=wrong_message
        self.wrong_redirect=wrong_redirect
        self.fail_image=fail_image
        self.redirect_after=redirect_after
        self.closed=False
        self.input=Element()
        self.button=Element()
    @property
    def current_url(self):
        if self.wrong_redirect or (self.redirect_after and self.button.clicked):
            return "https://evil.example/form"
        return self.url
    def get(self, url):
        assert url == module.PUBLIC_URL
    def find_element(self, by, value):
        assert (by,value) in [("name","my-text"),("css selector","button"),("id","message")]
        if value=="my-text":return self.input
        if value=="button":return self.button
        return Element("Unexpected" if self.wrong_message else "Received!")
    def save_screenshot(self, file):
        if self.fail_image:return False
        Path(file).write_bytes(b"fake image bytes for unit test"+Path(file).name.encode())
        return True
    def quit(self):
        self.closed=True


def test_cli_defaults_to_plan(capsys):
    assert module.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"]=="dry_run"
    assert not report["browser_launched"]
    assert not report["network_used"]


def test_fake_driver_once(monkeypatch,capsys):
    driver=FakeDriver()
    assert module.main(["--run-public-demo"],driver_factory=lambda:driver)==0
    out=json.loads(capsys.readouterr().out)
    assert out["report"]["site_test_smoke_passed"]
    assert not out["report"]["customer_db_access_authorized"]
    assert not out["report"]["mapped_ui_controls_enabled"]
    assert driver.input.typed==module.DEMO_INPUT
    assert driver.button.clicked
    assert driver.closed
    assert (Path(out["capture_dir"])/"before.png").exists()
    assert (Path(out["capture_dir"])/"after.png").exists()
    assert (Path(out["capture_dir"])/"capture_report.json").exists()
    import shutil
    shutil.rmtree(out["capture_dir"])


@pytest.mark.parametrize("options",["wrong_message", "wrong_redirect", "fail_image", "redirect_after"])
def test_failure_closed_once(options,capsys):
    drv=FakeDriver(**{options:True})
    assert module.main(["--run-public-demo"],driver_factory=lambda:drv)==1
    response=json.loads(capsys.readouterr().out)
    assert response["status"]=="failed_no_retry"
    assert drv.closed
    import shutil
    shutil.rmtree(response["capture_dir"])
