"""Offline, explicitly invoked fixed-public-reference analogue builder.

Invoke from repository root as `python -m scripts.build_public_form_analogue`.
Default prints a dry-run plan. --generate writes only a new operating system
system-temp directory and never opens a browser or contacts selenium.dev.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import uuid
from pathlib import Path

from astra_contracts.public_form_analogue import generate_analogue
from astra_contracts.public_reference_probe import PublicPageNote

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    p = argparse.ArgumentParser(description='Build a safe local public-form analogue from SHA-pinned excerpts')
    p.add_argument('--generate', action='store_true', help='create a new isolated local demo')
    args = p.parse_args(argv)
    fixtures = ROOT/'fixtures'
    note = PublicPageNote.model_validate_json((fixtures/'public_selenium_form_note_20261019.json').read_text(encoding='utf-8'))
    if not args.generate:
        print(json.dumps({'mode':'dry_run','demo_target':'own_local_process_only',
                          'remote_site_click_executed':False,'network_used':False,
                          'local_output_created':False},indent=2))
        return 0
    target = Path(tempfile.gettempdir())/('astra-public-form-'+uuid.uuid4().hex)
    report = generate_analogue(note,fixtures/'public_selenium_form_page_excerpt_20261019.txt',
                              fixtures/'public_selenium_official_docs_excerpt_20261019.txt',target)
    print(json.dumps({'generated_path':str(target),'manifest':report},indent=2,ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
