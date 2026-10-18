"""One fixed public-doc-backed, generated *analogue*, not a replica claim.

Reads only SHA-pinned, user-curated Selenium website and publisher-doc snippets.
Generates a fully isolated independent FastAPI HTML form that demonstrates the
published input -> submit -> Received! interaction with a self-owned handler.
There is no website scraping, page copying, browser automation, customer DB,
authentication, or permission inference.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from astra_contracts.public_reference_probe import PublicPageNote, audit_public_reference

ORIGINAL = 'https://www.selenium.dev/selenium/web/web-form.html'
DOCUMENTATION = 'https://www.selenium.dev/documentation/webdriver/getting_started/first_script/'

APP_SOURCE = '''"""Synthetic ASTRA public-reference form analogue; no live site behavior assertion."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from urllib.parse import parse_qs

app = FastAPI(title="ASTRA Form Analogue (synthetic)")
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent demo form</title><style>
body{font-family:system-ui,sans-serif;margin:4rem auto;max-width:35rem;padding:1rem;
background:#f8fafc;color:#0f172a}main{background:white;border:1px solid #cbd5e1;
padding:2rem;border-radius:1rem}input{display:block;width:100%;box-sizing:border-box;
padding:.8rem;margin:1rem 0;border:1px solid #64748b;border-radius:.4rem}
button{padding:.8rem 1.2rem;background:#0f5cc7;color:white;border:0;border-radius:.4rem;
cursor:pointer}.note{font-size:.8rem;color:#475569}</style></head><body><main>
<h1>Independent form demo</h1><p>Text input</p>
<form method="post" action="/submit"><label for="my-text">Text input</label>
<input id="my-text" name="my-text" type="text" maxlength="80" required>
<button type="submit">Submit</button></form>
<p class="note">Synthetic implementation based on public publisher documentation; no claim of copied source or confirmed original behavior.</p>
</main></body></html>"""
RESULT = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Form submitted</title></head><body><main><h1>Form submitted</h1>
<p id="message">Received!</p><a href="/">Return</a></main></body></html>"""

@app.get("/health")
def health():
    return {"synthetic":True,"status":"ok","original_site_interaction_verified":False}

@app.get("/", response_class=HTMLResponse)
def page():
    return PAGE

@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    if request.headers.get("content-type", "").split(";",1)[0].lower().strip() != "application/x-www-form-urlencoded":
        raise HTTPException(status_code=415, detail="form encoding required")
    if request.headers.get("content-length") and int(request.headers["content-length"]) > 1024:
        raise HTTPException(status_code=413, detail="form too long")
    payload = await request.body()
    if len(payload) > 1024:
        raise HTTPException(status_code=413, detail="form too long")
    try:
        decoded = payload.decode("utf-8", errors="strict")
        fields = parse_qs(decoded,keep_blank_values=True,strict_parsing=True,max_num_fields=1,errors="strict")
    except (UnicodeDecodeError,ValueError):
        raise HTTPException(status_code=422, detail="malformed form")
    if set(fields) != {"my-text"} or len(fields["my-text"]) != 1:
        raise HTTPException(status_code=422, detail="unexpected form input")
    value = fields["my-text"][0]
    if not 1 <= len(value) <= 80 or any(ord(c)<32 for c in value):
        raise HTTPException(status_code=422, detail="invalid form input")
    # Do not echo text, store it, or submit it to an external endpoint.
    return RESULT
'''

README = '''# ASTRA isolated form analogue

Run `python -m uvicorn app:app --host 127.0.0.1 --port 8019` in this directory.
Visit http://127.0.0.1:8019/. Enter fictional text and press Submit; this
independent local demo renders `Received!` at POST /submit.

**Evidence**: publisher documentation for Selenium's public Web form describes
`my-text` input, Submit, and `Received!`; an openly readable result page also
shows `Received!`. **No actual remote submission or screenshot has been made**.
The choice to implement POST /submit is our own design, NOT an inferred remote
network contract. No copy of the original site's HTML/JS, credentials, DB,
customer mapping, or production authorization is included. Never deploy without
adding authentication, reviews, and other protections appropriate to your data.
'''


def _safe_output_dir(output_dir: Path):
    output_dir = Path(output_dir)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (not output_dir.is_absolute() or output_dir.is_symlink() or output_dir.exists()
            or output_dir.parent.is_symlink() or output_dir.parent.resolve() != temp_root
            or not output_dir.name.startswith('astra-public-form-')):
        raise ValueError('generation destination must be a fresh astra-public-form-* temp-root child')


def generate_analogue(note: PublicPageNote, page_excerpt: Path,
                      docs_excerpt: Path, output_dir: Path) -> dict:
    """Fail closed *before* any creation; no supplied code or untrusted text is embedded."""
    note = PublicPageNote.model_validate(note.model_dump(mode='json'))
    report = audit_public_reference(note, page_excerpt, docs_excerpt)
    if (note.reference_url != ORIGINAL or note.documentation_url != DOCUMENTATION
            or note.documented_input_selector != 'my-text'
            or note.documented_result_token != 'Received!'
            or note.input_token != 'Text input' or note.submit_token != 'Submit'):
        raise ValueError('fixed public publisher recipe not supported')
    _safe_output_dir(output_dir)
    output_dir.mkdir(mode=0o700)
    manifest = {
        'version':'0.1', 'classification':'public_documentation_based_synthetic_analogue',
        'reference_url':ORIGINAL, 'documentation_url':DOCUMENTATION,
        'page_excerpt_sha256':report.page_excerpt_sha256,
        'docs_excerpt_sha256':report.docs_excerpt_sha256,
        'page_evidence_id':report.page_evidence_id,
        'docs_evidence_id':report.docs_evidence_id,
        'local_route':'POST /submit', 'input_selector':'my-text',
        'expected_local_result':'Received!',
        'original_site_click_executed':False,'original_site_behavior_verified':False,
        'source_code_copied':False,'customer_db_or_api_connected':False,
        'deployment_authorized':False,'ui_mapping_approved':False,
    }
    files = {
        'app.py':APP_SOURCE,
        'README.md':README,
        'requirements.txt':'fastapi>=0.115,<1\nuvicorn>=0.30,<1\n',
        'provenance.json':json.dumps(manifest,sort_keys=True,indent=2)+'\n',
    }
    for filename, value in files.items():
        (output_dir / filename).write_text(value,encoding='utf-8')
    manifest['generated_file_sha256'] = {
        name:hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        for name in files
    }
    return manifest
