"""Opt-in firsthand Selenium public-form probe for a locally controlled browser.

No website interaction, credentials, browser startup or file writes by default.
`--run` requires an operator's working Chrome/WebDriver and only navigates the
fixed, openly published Selenium demonstration; generates redacted review-only
snapshots consumable by ASTRA's preexisting capture_intake tooling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

from astra_contracts.observation import ObservationBundle

FORM = 'https://www.selenium.dev/selenium/web/web-form.html'
RESULT = 'https://www.selenium.dev/selenium/web/submitted-form.html'
TEST_TEXT = 'ASTRA publicly documented demo only'
ACTION = 'Enter fixed fictional text into my-text and click Submit'


def _exact_url(value: str, expected: str) -> None:
    # Refuse redirects to other origins and unexpected query/fragment/userinfo.
    parts = urlsplit(value)
    if value != expected or (parts.scheme, parts.hostname, parts.port) != ('https', 'www.selenium.dev', None):
        raise ValueError('unexpected source URL or redirect; do not capture')


def _expected_result_url(value: str) -> None:
    """GET forms can submit fixed demo fields as a URL query: never store it."""
    parts = urlsplit(value)
    expected = urlsplit(RESULT)
    disallowed = {'access_token', 'refresh_token', 'password', 'token', 'api_key',
                  'secret', 'authorization', 'client_secret', 'session'}
    if (parts.scheme != 'https' or parts.hostname != 'www.selenium.dev'
            or parts.username is not None or parts.password is not None
            or parts.port is not None or parts.path != expected.path
            or parts.fragment or len(parts.query) > 4096
            or any(k.lower() in disallowed for k, _ in parse_qsl(parts.query, keep_blank_values=True))):
        raise ValueError('unexpected source URL or redirect; do not capture')


@dataclass(frozen=True)
class ProbeResult:
    before_time: datetime
    after_time: datetime
    before_message: str
    after_message: str
    first_url: str
    last_url: str


def capture_fixed_flow(driver, wait_for_received) -> ProbeResult:
    """Perform exactly one demo interaction; no raw HTML, session or network log."""
    driver.get(FORM)
    _exact_url(driver.current_url, FORM)
    input_control = driver.find_element('name', 'my-text')
    start_elements = driver.find_elements('id', 'message')
    if start_elements and any(element.text.strip() for element in start_elements):
        raise ValueError('unexpected pre-existing message')
    before_time = datetime.now(timezone.utc)
    before_message = ''
    input_control.send_keys(TEST_TEXT)
    driver.find_element('css selector', 'button').click()
    wait_for_received(driver)
    _expected_result_url(driver.current_url)
    after_message = driver.find_element('id', 'message').text.strip()
    if after_message != 'Received!':
        raise ValueError('publisher expected result not confirmed')
    after_time = datetime.now(timezone.utc)
    return ProbeResult(before_time, after_time, before_message, after_message, FORM, RESULT)


def _fingerprint(bundle: ObservationBundle) -> str:
    # Same canonical serialization as astra_contracts.generation_contract.fingerprint.
    raw = json.dumps(bundle.model_dump(mode='json'), sort_keys=True,
                     separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def make_review_package(probe: ProbeResult, root: Path) -> dict:
    """Write *only* redacted, bounded artifacts in a fresh system-temp child."""
    root = Path(root)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (not root.is_absolute() or root.exists() or root.is_symlink()
        or root.parent.is_symlink() or root.parent.resolve() != temp_root
        or not root.name.startswith('astra-selenium-public-')):
        raise ValueError('a new system-temp astra-selenium-public-* folder is required')
    _exact_url(probe.first_url, FORM)
    _expected_result_url(probe.last_url)
    if (probe.before_message != '' or probe.after_message != 'Received!'
        or probe.before_time.tzinfo is None or probe.after_time.tzinfo is None
        or probe.before_time.utcoffset() is None or probe.after_time.utcoffset() is None
        or probe.before_time > probe.after_time):
        raise ValueError('unverified or inconsistent fixed demo observation')
    # Never serialize field values, HTML, cookies, headers, or document source.
    before_text = 'source_url: ' + FORM + '\nfield_name: my-text\nmessage_text: (absent)\n'
    after_text = 'source_url: ' + RESULT + '\nresult_selector: #message\nmessage_text: Received!\n'
    bundle = ObservationBundle.model_validate({
        'schema_version':'1.0', 'site_url':FORM,
        'scope':'Operator-run public Selenium demo; independently unverified pending review',
        'recorded_at':probe.after_time.isoformat(), 'evidence':[],
        'observations':[{
            'id':'selenium_submit', 'feature':'navigation',
            'title':'Selenium public demonstration submit and result',
            'claim':'Local WebDriver run reported a Received! result; content, origin and action require independent review.',
            'certainty':'inferred', 'evidence_ids':[], 'action':ACTION,
            'before':{'result_message':probe.before_message},
            'after':{'result_message':probe.after_message},
        }],
    })
    request = {
        'version':'0.1', 'source_kind':'manually_supplied_local_files',
        'observation_sha256':_fingerprint(bundle),
        'captures':[
            {'evidence':{'id':'selenium_before','kind':'dom_text','source_ref':'evidence/before.txt',
                         'captured_at':probe.before_time.isoformat(),
                         'notes':'Automation-reported minimal DOM facts; untrusted pending review'},
             'observation_ids':['selenium_submit']},
            {'evidence':{'id':'selenium_after','kind':'dom_text','source_ref':'evidence/after.txt',
                         'captured_at':probe.after_time.isoformat(),
                         'notes':'Automation-reported minimal DOM facts; untrusted pending review'},
             'observation_ids':['selenium_submit']},
        ],
    }
    manifest = {
        'version':'0.1','mode':'operator_local_webdriver_claim_unreviewed',
        'original_site_behavior_verified':False,'user_approval_granted':False,
        'customer_data_accessed':False,'screenshot_captured':False,
        'sensitive_form_values_stored':False, 'generation_authorized':False,
        'deployment_authorized':False, 'observation_sha256':_fingerprint(bundle),
        'source_urls':[FORM,RESULT],
    }
    # Content is fully known and validated before output path creation.
    contents = {'evidence/before.txt':before_text,
                'evidence/after.txt':after_text,
                'bundle.json':bundle.model_dump_json(indent=2) + '\n',
                'request.json':json.dumps(request,indent=2,ensure_ascii=False) + '\n',
                'run_metadata.json':json.dumps(manifest,indent=2,ensure_ascii=False) + '\n'}
    root.mkdir(mode=0o700)
    (root/'evidence').mkdir(mode=0o700)
    for name, value in contents.items():
        with (root/name).open('x', encoding='utf-8') as fh:
            fh.write(value)
    return {'output_root':str(root), 'observation_sha256':_fingerprint(bundle),
            'file_count':len(contents), 'original_site_behavior_verified':False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Bounded Selenium public demonstration capture')
    parser.add_argument('--run',action='store_true',help='explicitly launch local Chrome and click one Selenium public form')
    args = parser.parse_args(argv)
    if not args.run:
        print(json.dumps({'mode':'dry_run','url':FORM,'browser_started':False,
                          'network_used':False,'files_written':False},indent=2))
        return 0
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        print('FAIL: Selenium unavailable; install selenium in your local Python environment',file=sys.stderr)
        return 2
    driver = None
    try:
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(20)
        def wait(driver):
            return WebDriverWait(driver, 10).until(
                lambda d: d.find_element('id','message').text.strip() == 'Received!')
        observation = capture_fixed_flow(driver,wait)
        import uuid
        target = Path(tempfile.gettempdir())/('astra-selenium-public-' + uuid.uuid4().hex)
        report = make_review_package(observation,target)
    except Exception as exc:
        print(f'FAIL: public Selenium demo capture unavailable: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.quit()
    print(json.dumps(report,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
