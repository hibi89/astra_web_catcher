"""Offline WebDriver fakes: executable capture recipe, not a live-site pass."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.public_selenium_capture import (
    FORM, RESULT, ProbeResult, TEST_TEXT, _fingerprint, _exact_url,
    capture_fixed_flow, make_review_package, main,
)
from astra_contracts.observation import ObservationBundle


class Field:
    def __init__(self, driver, kind):
        self.driver=driver
        self.kind=kind
    def send_keys(self, text):
        assert self.kind == 'input'
        self.driver.typed=text
    def click(self):
        assert self.kind == 'button'
        self.driver.clicked=True
        self.driver.current_url=self.driver.destination
    @property
    def text(self):
        assert self.kind == 'message'
        return self.driver.message


class Driver:
    def __init__(self, initial=FORM, destination=RESULT, message='Received!', prefilled=''):
        self.current_url=initial
        self.destination=destination
        self.message=message
        self.prefilled=prefilled
        self.clicked=False
        self.typed=None
        self.visited=[]
    def get(self,url):
        self.visited.append(url)
    def find_elements(self, how, value):
        if (how, value)==('id','message') and self.prefilled:
            class Pre:
                text=self.prefilled
            return [Pre()]
        return []
    def find_element(self, how, value):
        if (how,value)==('name','my-text'):return Field(self,'input')
        if (how,value)==('css selector','button'):return Field(self,'button')
        if (how,value)==('id','message'):return Field(self,'message')
        raise ValueError('not allowlisted control')


def wait(d):
    assert d.clicked


def fresh():
    return Path(tempfile.gettempdir())/('astra-selenium-public-'+uuid.uuid4().hex)


@pytest.fixture
def successful():
    d=Driver()
    report=capture_fixed_flow(d,wait)
    assert d.typed == TEST_TEXT
    assert d.clicked and d.visited==[FORM]
    return report


def test_fixed_flow_live_driver_protocol_synthetic(successful):
    assert successful.first_url==FORM
    assert successful.last_url==RESULT
    assert successful.before_message=='' and successful.after_message=='Received!'
    assert successful.before_time <= successful.after_time
    assert successful.before_time.tzinfo and successful.after_time.tzinfo


@pytest.mark.parametrize('invalid',[ 'http://www.selenium.dev/selenium/web/web-form.html',
    'https://evil.example/selenium/web/web-form.html',
    FORM+'?access_token=oops',FORM+'#hash',
    'https://www.selenium.dev:443/selenium/web/web-form.html',
    'https://www.selenium.dev@evil.example/selenium/web/web-form.html'])
def test_unexpected_origin_fails_before_click(invalid):
    d=Driver(initial=invalid)
    with pytest.raises(ValueError,match='unexpected source URL'):
        capture_fixed_flow(d,wait)
    assert not d.clicked and d.typed is None


@pytest.mark.parametrize('dest',[ 'https://evil.example/landing',FORM,RESULT+'?other=value'])
def test_unexpected_submit_redirect_fails(dest):
    d=Driver(destination=dest)
    with pytest.raises(ValueError,match='unexpected source URL'):
        capture_fixed_flow(d,wait)
    assert d.clicked


def test_changed_expected_message_blocks():
    with pytest.raises(ValueError,match='expected result'):
        capture_fixed_flow(Driver(message='Not received'),wait)


def test_prefilled_existing_message_blocks():
    d=Driver(prefilled='sensitive notice')
    with pytest.raises(ValueError,match='pre-existing'):
        capture_fixed_flow(d,wait)
    assert not d.clicked


def test_package_has_valid_models_and_zero_approval(successful):
    target=fresh()
    try:
        result=make_review_package(successful,target)
        assert result['file_count']==5 and not result['original_site_behavior_verified']
        bundle=ObservationBundle.model_validate_json((target/'bundle.json').read_text())
        request=json.loads((target/'request.json').read_text())
        assert request['observation_sha256']==_fingerprint(bundle)
        assert bundle.observations[0].certainty.value=='inferred'
        assert bundle.observations[0].evidence_ids==[]
        assert bundle.observations[0].before=={'result_message':''}
        assert bundle.observations[0].after=={'result_message':'Received!'}
        assert request['source_kind']=='manually_supplied_local_files'
        assert len(request['captures'])==2
        assert {e['evidence']['kind'] for e in request['captures']}=={'dom_text'}
        meta=json.loads((target/'run_metadata.json').read_text())
        for key in ('original_site_behavior_verified','user_approval_granted','customer_data_accessed',
                    'screenshot_captured','sensitive_form_values_stored','generation_authorized',
                    'deployment_authorized'):
            assert meta[key] is False
        assert TEST_TEXT not in '\n'.join(p.read_text() for p in target.rglob('*') if p.is_file())
        assert all(not any(x in p.read_text() for x in ('cookie','password','Bearer'))
                   for p in target.rglob('*.txt'))
    finally:
        import shutil
        if target.exists():shutil.rmtree(target)


def test_package_disallows_existing_destination(successful):
    with tempfile.TemporaryDirectory(prefix='astra-selenium-public-') as root:
        p=Path(root)
        (p/'keep.txt').write_text('KEEP')
        with pytest.raises(ValueError,match='new system-temp'):
            make_review_package(successful,p)
        assert (p/'keep.txt').read_text()=='KEEP'


def test_package_disallows_non_temp_directory(successful,tmp_path):
    with pytest.raises(ValueError,match='new system-temp'):
        make_review_package(successful,tmp_path/'astra-selenium-public-test')


def test_package_rejects_fake_result_before_writing(successful):
    target=fresh()
    with pytest.raises(ValueError,match='inconsistent'):
        make_review_package(replace(successful,after_message='Other'),target)
    assert not target.exists()


def test_package_rejects_reversed_timestamps(successful):
    target=fresh()
    with pytest.raises(ValueError,match='inconsistent'):
        make_review_package(replace(successful,after_time=successful.before_time-timedelta(minutes=1)),target)
    assert not target.exists()


def test_package_rejects_naive_datetime(successful):
    target=fresh()
    with pytest.raises(ValueError,match='inconsistent'):
        make_review_package(replace(successful,before_time=datetime(2026,10,19,1,1)),target)
    assert not target.exists()


def test_default_cli_dry_run_is_offline(capsys):
    assert main([])==0
    data=json.loads(capsys.readouterr().out)
    assert data['browser_started'] is False and data['network_used'] is False
    assert data['files_written'] is False


def test_standard_module_command_dry_run():
    root=Path(__file__).resolve().parents[1]
    r=subprocess.run([sys.executable,'-m','scripts.public_selenium_capture'],cwd=root,
                     capture_output=True,text=True,timeout=5)
    assert r.returncode==0, r.stderr
    assert json.loads(r.stdout)['mode']=='dry_run'
