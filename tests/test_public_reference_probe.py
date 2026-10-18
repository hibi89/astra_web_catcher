"""A web tool excerpt or publisher tutorial never becomes first-hand browser evidence."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.public_reference_probe import (
    PublicPageNote, audit_public_reference, public_https,
)

ROOT = Path(__file__).resolve().parents[1] / "fixtures"
PAGE = ROOT / "public_selenium_form_page_excerpt_20261019.txt"
DOCS = ROOT / "public_selenium_official_docs_excerpt_20261019.txt"
NOTE = ROOT / "public_selenium_form_note_20261019.json"


def case():
    return PublicPageNote.model_validate_json(NOTE.read_text(encoding="utf-8"))


def test_real_public_page_passive_audit():
    result = audit_public_reference(case(), PAGE, DOCS)
    assert result.visible_control_labels_found == ["Text input", "Submit"]
    assert result.documented_input_selector == "my-text"
    assert result.documented_result_token == "Received!"
    assert result.status == "public_page_readonly_and_publisher_documented_only"
    assert not result.live_browser_click_verified
    assert not result.original_site_behavior_verified
    assert not result.external_content_authenticated
    assert not result.ui_mapping_enabled
    assert not result.generation_authorized


@pytest.mark.parametrize("bad", [
    "http://example.com/a", "https://localhost/a", "https://127.0.0.1/a",
    "https://10.0.0.2/a", "https://[::1]/a", "https://example.local/a",
    "https://username:pwd@example.com/a", "https://example.com:8000/a",
    "https://example.com/a?x=1", "https://example.com/a#fragment",
    "file:///secret", "https://example.com.evil.local/a", "https://example.com..evil/a",
])
def test_url_rejected(bad):
    with pytest.raises((ValueError, ValidationError)):
        public_https(bad)


def test_official_host_mismatch_rejected():
    payload = case().model_dump()
    payload["documentation_url"] = "https://another.example.com/docs"
    with pytest.raises(ValidationError):
        PublicPageNote.model_validate(payload)


@pytest.mark.parametrize("field", ["click_executed_by_this_audit", "original_site_behavior_verified",
                                   "human_authentication_verified", "owner_db_access_authorized",
                                   "deployment_authorized", "source_html_captured", "screenshot_captured"])
def test_authority_flags_cannot_be_forged(field):
    payload = case().model_dump()
    payload[field] = True
    with pytest.raises(ValidationError):
        PublicPageNote.model_validate(payload)


def test_unknown_flag_rejected():
    payload = case().model_dump()
    payload["site_scraped_live"] = True
    with pytest.raises(ValidationError):
        PublicPageNote.model_validate(payload)


def test_tampered_page_fails(tmp_path):
    alt = tmp_path / "page.txt"
    alt.write_bytes(PAGE.read_bytes()+b" edited")
    with pytest.raises(ValueError,match="SHA-256"):
        audit_public_reference(case(), alt, DOCS)


def test_tampered_docs_fails(tmp_path):
    alt = tmp_path / "docs.txt"
    alt.write_bytes(DOCS.read_bytes()+b" edited")
    with pytest.raises(ValueError,match="SHA-256"):
        audit_public_reference(case(), PAGE, alt)


def test_missing_visible_control_rejected(tmp_path):
    alt = tmp_path / "page.txt"
    alt.write_text("Web form\nText input",encoding="utf-8")
    data=case().model_dump()
    data["page_excerpt_sha256"]=hashlib.sha256(alt.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match="visible controls"):
        audit_public_reference(PublicPageNote.model_validate(data),alt,DOCS)


def test_unsubstantiated_documentation_claim_rejected(tmp_path):
    alt = tmp_path / "docs.txt"
    alt.write_text("my-text but no published outcome",encoding="utf-8")
    data=case().model_dump()
    data["docs_excerpt_sha256"]=hashlib.sha256(alt.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match="recipe"):
        audit_public_reference(PublicPageNote.model_validate(data),PAGE,alt)


def test_symlink_rejected(tmp_path):
    lnk=tmp_path/"page.txt"
    lnk.symlink_to(PAGE)
    with pytest.raises(ValueError,match="symlinked"):
        audit_public_reference(case(),lnk,DOCS)


def test_no_network_code_import(monkeypatch):
    # Pure package audit uses only provided local files and never launches a browser.
    audit_public_reference(case(),PAGE,DOCS)


def test_golden_public_reference_report_stable():
    expected = json.loads((ROOT / "public_selenium_passive_probe_report_20261019.json").read_text(encoding="utf-8"))
    assert audit_public_reference(case(), PAGE, DOCS).model_dump(mode="json") == expected
