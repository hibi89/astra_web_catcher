"""Second fixed publisher-documented feature: independent, local checkbox analogue.

Only an explicitly pinned human-curated excerpt is read. This does not visit,
click, infer a network contract, or copy code from the publisher's website.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import uuid
from pathlib import Path

TARGET = "https://www.selenium.dev/selenium/web/inputs.html"
DOCUMENTATION = "https://www.selenium.dev/documentation/webdriver/elements/interactions/"
EXCERPT_SHA256 = "f30a95e76858e168a1c7c1948a1961a08ee9fae47fa438e5e5f3bcb7b88a4ca1"
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/public_selenium_checkbox_excerpt_20261019.txt"

APP_SOURCE = '''"""Independent local checkbox analogue, not a Selenium site replica."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

app = FastAPI(title="ASTRA independent checkbox demo")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local checkbox demo</title></head><body><main>
<h1>Independent checkbox demo</h1>
<label for="checkbox_input"><input type="checkbox" id="checkbox_input"
 name="checkbox_input" checked> Example checkbox</label>
<p id="selection-state" role="status" aria-live="polite">Checked</p>
<p>Local synthetic behavior. No original-site interaction was verified.</p>
</main><script src="/controller.js" defer></script></body></html>"""
SCRIPT = """'use strict';
const box = document.getElementById('checkbox_input');
const state = document.getElementById('selection-state');
box.addEventListener('change', () => {
  state.textContent = box.checked ? 'Checked' : 'Unchecked';
});
"""

@app.get('/health')
def health():
    return {'status': 'ok', 'synthetic': True, 'original_site_click_verified': False}

@app.get('/', response_class=HTMLResponse)
def index():
    return HTMLResponse(PAGE, headers={'Cache-Control':'no-store',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; base-uri 'none'; form-action 'none'",
        'X-Content-Type-Options':'nosniff'})

@app.get('/controller.js')
def script():
    return Response(SCRIPT, media_type='application/javascript',
        headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
'''

README = '''# ASTRA publisher-documented checkbox analogue

Run `python -m uvicorn app:app --host 127.0.0.1 --port 8020` in this generated folder.
Check/uncheck the box locally; the status changes from Checked to Unchecked and back.
This is independently authored synthetic behavior grounded in the Selenium
publisher's checkbox interaction tutorial, not verified behavior of its live
website. No external requests, source HTML copying, API or DB integration.
Never publicly deploy this unauthenticated demonstration.
'''


def _check_evidence(path: Path) -> str:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise ValueError('missing, symlinked or excessive evidence')
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXCERPT_SHA256:
        raise ValueError('publisher excerpt SHA-256 mismatch')
    content = data.decode('utf-8')
    if not all(v in content for v in (TARGET, DOCUMENTATION, 'checkbox_input', 'click()', 'is_selected()', 'False')):
        raise ValueError('fixed publisher checkbox recipe unsupported')
    return digest


def _check_target(output: Path) -> None:
    output = Path(output)
    root = Path(tempfile.gettempdir()).resolve()
    if (not output.is_absolute() or output.exists() or output.is_symlink()
        or output.parent.is_symlink() or output.parent.resolve() != root
        or not output.name.startswith('astra-public-checkbox-')):
        raise ValueError('output must be a fresh astra-public-checkbox-* temp child')


def generate_checkbox_analogue(evidence: Path, output: Path) -> dict:
    """Fail closed before creating a temp output; emit only static authored assets."""
    digest = _check_evidence(evidence)
    _check_target(output)
    output = Path(output)
    output.mkdir(mode=0o700)
    manifest = {
        'version': '0.1', 'classification': 'fixed_documented_checkbox_synthetic_analogue',
        'reference_url': TARGET, 'documentation_url': DOCUMENTATION,
        'evidence_kind': 'human_curated_publisher_excerpt', 'evidence_sha256': digest,
        'local_control_name': 'checkbox_input', 'local_initial_state': True,
        'local_first_click_state': False,
        'original_site_click_executed': False, 'original_initial_state_verified': False,
        'original_site_behavior_verified': False, 'source_code_copied': False,
        'customer_db_or_api_connected': False, 'deployment_authorized': False,
        'generation_contract': 'blocked_pending_review',
    }
    files = {
        'app.py': APP_SOURCE, 'README.md': README,
        'requirements.txt': 'fastapi>=0.115,<1\nuvicorn>=0.30,<1\n',
        'provenance.json': json.dumps(manifest, indent=2, sort_keys=True) + '\n',
    }
    for name, content in files.items():
        (output / name).write_text(content, encoding='utf-8')
    return {**manifest, 'generated_file_sha256': {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in files
    }}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Generate a fixed local checkbox analogue')
    parser.add_argument('--generate', action='store_true', help='create a new temp-only local demo')
    args = parser.parse_args(argv)
    _check_evidence(FIXTURE)
    if not args.generate:
        print(json.dumps({'mode': 'dry_run', 'network_used': False,
                          'local_output_created': False, 'reference_url': TARGET}))
        return 0
    output = Path(tempfile.gettempdir()) / ('astra-public-checkbox-' + uuid.uuid4().hex)
    report = generate_checkbox_analogue(FIXTURE, output)
    print(json.dumps({'generated_path': str(output), 'manifest': report}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
