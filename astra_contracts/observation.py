"""Observation evidence contract (v1), independent of live sites and user databases.

Usage:
    python -m astra_contracts.observation validate fixtures/observation_brand_filter.json
    python -m astra_contracts.observation schema

This module describes observed public UI behaviour; it does not crawl, execute,
write to a database, or generate any new service.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


ID_PATTERN = r"^[a-z][a-z0-9_-]{1,63}$"
SECRET_FIELD = re.compile(r"(^|[_\-])(authorization|cookie|passwd|password|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|session|bearer|client[_-]?secret)([_\-]|$)", re.I)
FORBIDDEN_QUERY = {"access_token", "refresh_token", "token", "key", "api_key", "password", "secret", "authorization", "session", "code", "client_secret"}


def clean_url(url: str) -> str:
    """Require a http(s) URL with no embedded credentials or obvious secret query keys."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("URL must have an http(s) scheme and hostname")
        if parts.username is not None or parts.password is not None:
            raise ValueError("URL must not contain embedded credentials")
        if any(k.lower() in FORBIDDEN_QUERY for k, _ in parse_qsl(parts.query, keep_blank_values=True)):
            raise ValueError("URL must not contain credential query parameters")
        return url
    except ValueError as exc:
        raise ValueError(f"Unsafe or invalid URL: {exc}") from exc


def clean_state(value: dict[str, Any]) -> dict[str, Any]:
    """Allow only JSON-safe scalar UI facts, avoiding secret fields and raw payloads."""
    for key, item in value.items():
        if SECRET_FIELD.search(key):
            raise ValueError("UI state contains a credential-like field name")
        if not isinstance(item, (str, int, float, bool, type(None))):
            raise ValueError("UI state only accepts JSON scalar values; no nested/raw payloads")
        if isinstance(item, str) and len(item) > 250:
            raise ValueError("UI state string is too long")
    return value


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceKind(str, Enum):
    SCREENSHOT = "screenshot"
    DOM_TEXT = "dom_text"
    USER_DEMONSTRATION = "user_demonstration"
    SANITIZED_NETWORK = "sanitized_network"
    MANUAL_TEST = "manual_test"
    ARCHIVED_REPORT = "archived_report"  # secondary written account, not raw screenshot evidence


class Certainty(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Feature(str, Enum):
    NAVIGATION = "navigation"
    LIST = "list"
    SEARCH = "search"
    FILTER = "filter"
    DETAIL = "detail"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BASIC_AGGREGATE = "basic_aggregate"


class Evidence(ClosedModel):
    id: str = Field(pattern=ID_PATTERN)
    kind: EvidenceKind
    source_ref: str = Field(min_length=1, max_length=260, description="Redacted, local relative reference, never a full HAR or credential URL")
    captured_at: datetime
    notes: str = Field(default="", max_length=500)

    @field_validator("captured_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at requires an explicit timezone")
        return value

    @field_validator("source_ref")
    @classmethod
    def safe_local_ref(cls, value: str) -> str:
        if value.startswith(("/", "\\")) or "\\" in value or ".." in Path(value).parts or urlsplit(value).scheme or "?" in value or "#" in value:
            raise ValueError("source_ref must be a clean relative path")
        if SECRET_FIELD.search(value):
            raise ValueError("source_ref contains a credential-like name")
        return value


class UIObservation(ClosedModel):
    id: str = Field(pattern=ID_PATTERN)
    feature: Feature
    title: str = Field(min_length=1, max_length=160)
    claim: str = Field(min_length=1, max_length=700)
    certainty: Certainty
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    action: str | None = Field(default=None, max_length=250)
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)

    @field_validator("before", "after")
    @classmethod
    def state_is_safe(cls, value: dict[str, Any]) -> dict[str, Any]:
        return clean_state(value)

    @model_validator(mode="after")
    def provenance(self) -> "UIObservation":
        if self.certainty is Certainty.OBSERVED and not self.evidence_ids:
            raise ValueError("observed claims require at least one evidence ID")
        if self.certainty is Certainty.UNKNOWN and self.evidence_ids:
            raise ValueError("unknown claims cannot be asserted as evidence-backed")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("duplicate evidence reference")
        return self


class ObservationBundle(ClosedModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    site_url: str
    scope: str = Field(min_length=1, max_length=250)
    recorded_at: datetime
    evidence: list[Evidence] = Field(default_factory=list, max_length=200)
    observations: list[UIObservation] = Field(default_factory=list, min_length=1, max_length=500)

    @field_validator("site_url")
    @classmethod
    def valid_site_url(cls, value: str) -> str:
        return clean_url(value)

    @field_validator("recorded_at")
    @classmethod
    def record_time_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at requires an explicit timezone")
        return value

    @model_validator(mode="after")
    def cross_references(self) -> "ObservationBundle":
        ev_ids = [ev.id for ev in self.evidence]
        ob_ids = [ob.id for ob in self.observations]
        if len(ev_ids) != len(set(ev_ids)) or len(ob_ids) != len(set(ob_ids)):
            raise ValueError("duplicate evidence/observation IDs")
        missing = sorted({rid for item in self.observations for rid in item.evidence_ids} - set(ev_ids))
        if missing:
            raise ValueError(f"unknown evidence IDs: {', '.join(missing)}")
        return self


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Read-only UI observation evidence contract (v1)")
    cli.add_argument("command", choices=["validate", "schema"])
    cli.add_argument("file", nargs="?", help="Path to observation JSON (validate only)")
    args = cli.parse_args(argv)
    if args.command == "schema":
        if args.file:
            cli.error("schema takes no file")
        print(json.dumps(ObservationBundle.model_json_schema(), ensure_ascii=False, indent=2))
        return 0
    if not args.file:
        cli.error("validate requires a JSON file")
    try:
        value = json.loads(Path(args.file).read_text(encoding="utf-8"))
        bundle = ObservationBundle.model_validate(value)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"FAIL: invalid observation bundle: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {len(bundle.observations)} observations; {len(bundle.evidence)} evidence items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
