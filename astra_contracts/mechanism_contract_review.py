"""Offline, fail-closed comparison of two documented *local* demo mechanisms.

This checks pinned repository files, not the remote website. No browser,
network, code execution from evidence, generator invocation, or file writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Mechanism:
    key: str
    source: str
    source_blob_sha1: str
    evidence: tuple[tuple[str, str], ...]
    reference_url: str
    documentation_url: str
    local_input: str
    trigger: Literal['submit', 'change']
    local_output: str
    transport: Literal['own_local_http_post', 'own_local_dom_event']
    behavior_evidence: Literal['publisher_documented_not_live_verified'] = 'publisher_documented_not_live_verified'


SUPPORTED = (
    Mechanism(
        key='text_form', source='astra_contracts/public_form_analogue.py',
        source_blob_sha1='82670b1e797d2473fe7c3262f8e28b282afd13c5',
        evidence=(
            ('fixtures/public_selenium_form_page_excerpt_20261019.txt',
             '1bee345696adb474fb811365f993ee0327ef9f9e6fecfb1b3f94370c4f87a763'),
            ('fixtures/public_selenium_official_docs_excerpt_20261019.txt',
             '4a1cdf8a12978454e6321a4275bf51c0954611e9e2c09f8659ccb96648e55979'),
        ),
        reference_url='https://www.selenium.dev/selenium/web/web-form.html',
        documentation_url='https://www.selenium.dev/documentation/webdriver/getting_started/first_script/',
        local_input='my-text', trigger='submit', local_output='Received!',
        transport='own_local_http_post',
    ),
    Mechanism(
        key='checkbox', source='astra_contracts/public_checkbox_analogue.py',
        source_blob_sha1='ecf1239dc5c2b7c2966ba03fe8793164d89ae5a7',
        evidence=((
            'fixtures/public_selenium_checkbox_excerpt_20261019.txt',
            'f30a95e76858e168a1c7c1948a1961a08ee9fae47fa438e5e5f3bcb7b88a4ca1',
        ),),
        reference_url='https://www.selenium.dev/selenium/web/inputs.html',
        documentation_url='https://www.selenium.dev/documentation/webdriver/elements/interactions/',
        local_input='checkbox_input', trigger='change', local_output='Checked / Unchecked',
        transport='own_local_dom_event',
    ),
)


def _checked_bytes(root: Path, relative: str, maximum: int = 100_000) -> bytes:
    if relative.startswith('/') or '\\' in relative or '..' in Path(relative).parts:
        raise ValueError('unsafe relative path')
    path = root / relative
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'symlink input or ancestor: {relative}')
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError(f'missing, symlink or oversized input: {relative}')
    if not path.resolve().is_relative_to(root):
        raise ValueError('input escaped the repository root')
    return path.read_bytes()


def _validate_recipes(recipes: tuple[Mechanism, ...]) -> None:
    if len(recipes) != 2 or {r.key for r in recipes} != {'text_form', 'checkbox'}:
        raise ValueError('exactly two distinct approved review recipe slots required')
    if ({r.trigger for r in recipes} != {'submit', 'change'}
            or {r.transport for r in recipes} != {'own_local_http_post', 'own_local_dom_event'}):
        raise ValueError('demonstration mechanism types must remain distinct')
    if any(r.behavior_evidence != 'publisher_documented_not_live_verified' for r in recipes):
        raise ValueError('provenance cannot be upgraded by a local review')
    by_key = {r.key: r for r in recipes}
    for name, expected in {
        'text_form': ('astra_contracts/public_form_analogue.py', 'my-text', 'submit', 'Received!', 'own_local_http_post',
            'https://www.selenium.dev/selenium/web/web-form.html',
            'https://www.selenium.dev/documentation/webdriver/getting_started/first_script/'),
        'checkbox': ('astra_contracts/public_checkbox_analogue.py', 'checkbox_input', 'change', 'Checked / Unchecked', 'own_local_dom_event',
            'https://www.selenium.dev/selenium/web/inputs.html',
            'https://www.selenium.dev/documentation/webdriver/elements/interactions/'),
    }.items():
        r = by_key[name]
        if (r.source, r.local_input, r.trigger, r.local_output, r.transport,
            r.reference_url, r.documentation_url) != expected:
            raise ValueError('fixed demonstrated contract fields must not be relabeled')
    for r in recipes:
        if (not SHA_RE.fullmatch(r.source_blob_sha1) or not r.evidence
                or any(not SHA256_RE.fullmatch(sha) for _, sha in r.evidence)
                or not r.reference_url.startswith('https://www.selenium.dev/')
                or not r.documentation_url.startswith('https://www.selenium.dev/')
                or not r.local_input or not r.local_output):
            raise ValueError('invalid fixed demo contract')


def compare_mechanisms(root: Path, recipes: tuple[Mechanism, ...] = SUPPORTED) -> dict:
    """Pure report: verify local source/evidence bytes; never grant authority."""
    root = Path(root).resolve(strict=True)
    _validate_recipes(recipes)
    controls = []
    for r in sorted(recipes, key=lambda v: v.key):
        source = _checked_bytes(root, r.source)
        digest = hashlib.sha1(b'blob %d\0' % len(source) + source).hexdigest()
        if digest != r.source_blob_sha1:
            raise ValueError(f'Git blob SHA mismatch: {r.key}')
        checked_evidence = []
        for name, expected in r.evidence:
            raw = _checked_bytes(root, name, maximum=20_000)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f'evidence SHA-256 mismatch: {r.key}')
            checked_evidence.append({'path': name, 'sha256': expected})
        controls.append({
            'id': r.key, 'reference_url': r.reference_url,
            'documentation_url': r.documentation_url,
            'source_path': r.source, 'git_blob_sha1': digest,
            'evidence_files': checked_evidence,
            'input': r.local_input, 'trigger': r.trigger,
            'local_output': r.local_output, 'transport': r.transport,
            'evidence_level': r.behavior_evidence,
            'local_functional_demo': True,
            'original_site_click_verified': False,
            'original_site_behavior_verified': False,
            'original_http_contract_verified': False,
        })
    return {
        'report_version': '0.1', 'review_state': 'review_only_no_approval',
        'control_count': len(controls), 'controls': controls,
        'common_contract_fields': ['input', 'trigger', 'local_output', 'evidence_level'],
        'transport_must_remain_per_control': True,
        'source_file_integrity_verified': True,
        'evidence_file_integrity_verified': True,
        'publisher_authenticity_verified': False,
        'original_site_live_interaction_verified': False,
        'customer_db_or_api_authorized': False,
        'generation_authorized': False,
        'deployment_authorized': False,
        'generation_contract': 'blocked_pending_review',
        'network_used': False,
        'files_written': False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Offline review-only demo contract comparison')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    print(json.dumps(compare_mechanisms(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
