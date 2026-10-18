"""Offline audit of externally retrieved public-page text and a publisher's test recipe.

This does NOT perform a click, prove site authenticity, or grant code/data permissions.
The two input files are human-curated summaries of read-only web results; they
are not raw HTTP responses, screenshots, or original source archives.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA256 = r"^[0-9a-f]{64}$"


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def public_https(url: str) -> str:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if (parsed.scheme != "https" or not hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.query or parsed.fragment
            or hostname.lower() != hostname or hostname.endswith(".local")
            or hostname in {"localhost", "localhost.localdomain"}
            or not re.fullmatch(r"[a-z0-9.-]+", hostname)
            or "." not in hostname or ".." in hostname):
        raise ValueError("reference must be plain HTTPS public-domain URL without credentials or query")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("IP literal is not a permitted reference target")
    return url


class PublicPageNote(Closed):
    version: Literal["0.1"] = "0.1"
    reference_url: str
    documentation_url: str
    capture_kind: Literal["human_curated_web_text_excerpt"] = "human_curated_web_text_excerpt"
    page_excerpt_sha256: str = Field(pattern=SHA256)
    docs_excerpt_sha256: str = Field(pattern=SHA256)
    page_evidence_id: str = Field(pattern=r"^turn[0-9]+view[0-9]+$")
    docs_evidence_id: str = Field(pattern=r"^turn[0-9]+view[0-9]+$")
    page_title_token: str = Field(min_length=3, max_length=80)
    input_token: str = Field(min_length=3, max_length=80)
    submit_token: str = Field(min_length=3, max_length=80)
    documented_input_selector: str = Field(min_length=3, max_length=80)
    documented_result_token: str = Field(min_length=3, max_length=80)
    click_executed_by_this_audit: Literal[False] = False
    human_authentication_verified: Literal[False] = False
    source_html_captured: Literal[False] = False
    screenshot_captured: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    owner_db_access_authorized: Literal[False] = False
    deployment_authorized: Literal[False] = False

    @model_validator(mode="after")
    def check_urls(self):
        public_https(self.reference_url)
        public_https(self.documentation_url)
        if urlsplit(self.reference_url).hostname != urlsplit(self.documentation_url).hostname:
            raise ValueError("page and its official documentation must be same host in this unit")
        return self


class PassivePublicReferenceReport(Closed):
    version: Literal["0.1"] = "0.1"
    status: Literal["public_page_readonly_and_publisher_documented_only"] = (
        "public_page_readonly_and_publisher_documented_only")
    source_reference_url: str
    documentation_url: str
    page_excerpt_sha256: str
    docs_excerpt_sha256: str
    page_evidence_id: str
    docs_evidence_id: str
    visible_control_labels_found: list[str]
    documented_input_selector: str
    documented_result_token: str
    public_page_readonly_text_consistent: Literal[True] = True
    publisher_recipe_consistent: Literal[True] = True
    live_browser_click_verified: Literal[False] = False
    original_site_behavior_verified: Literal[False] = False
    external_content_authenticated: Literal[False] = False
    user_permission_for_owner_db: Literal[False] = False
    generation_authorized: Literal[False] = False
    ui_mapping_enabled: Literal[False] = False
    next_step: Literal["independent_allowlisted_live_browser_before_after_capture_required"] = (
        "independent_allowlisted_live_browser_before_after_capture_required")


def _verified_excerpt(path: Path, sha256: str) -> str:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
        raise ValueError("excerpt missing, symlinked or too large")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != sha256:
        raise ValueError("excerpt SHA-256 mismatch")
    return content.decode("utf-8")


def audit_public_reference(note: PublicPageNote, page_path: Path, docs_path: Path) -> PassivePublicReferenceReport:
    note = PublicPageNote.model_validate(note.model_dump(mode="json"))
    page = _verified_excerpt(page_path, note.page_excerpt_sha256)
    docs = _verified_excerpt(docs_path, note.docs_excerpt_sha256)
    if not all(t in page for t in (note.page_title_token, note.input_token, note.submit_token)):
        raise ValueError("page visible controls not supported by the supplied excerpt")
    if not all(t in docs for t in (note.documented_input_selector, note.documented_result_token)):
        raise ValueError("publisher's submitted-input/result recipe not found in excerpt")
    return PassivePublicReferenceReport(
        source_reference_url=note.reference_url, documentation_url=note.documentation_url,
        page_excerpt_sha256=note.page_excerpt_sha256, docs_excerpt_sha256=note.docs_excerpt_sha256,
        page_evidence_id=note.page_evidence_id, docs_evidence_id=note.docs_evidence_id,
        visible_control_labels_found=[note.input_token, note.submit_token],
        documented_input_selector=note.documented_input_selector,
        documented_result_token=note.documented_result_token,
    )


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Offline public-page text provenance triage; no browser or network")
    parser.add_argument("note", type=Path)
    parser.add_argument("page_excerpt", type=Path)
    parser.add_argument("docs_excerpt", type=Path)
    args = parser.parse_args(argv)
    note = PublicPageNote.model_validate_json(args.note.read_text(encoding="utf-8"))
    print(audit_public_reference(note, args.page_excerpt, args.docs_excerpt).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
