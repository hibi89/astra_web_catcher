"""Step 4-C isolated synthetic generator tests; no original project writes."""
from __future__ import annotations
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from astra_contracts.synthetic_generator import SyntheticDemo, generate_synthetic, main
from astra_contracts.generation_contract import GenerationContract

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'fixtures/synthetic_demo_catalog_20261018.json'

def fixture_data():
    return json.loads(SOURCE.read_text(encoding='utf-8'))

def project(tmp_path):
    # Use platform temp and existing, empty isolated output folder.
    d=Path(tempfile.mkdtemp(prefix='astra-synth-'))
    try:
        yield d
    finally:
        # Created synthetic files are disposable only; never touch user project.
        import shutil
        shutil.rmtree(d)


def test_generation_writes_seven_actual_scaffold_files():
    for d in project(None):
        output=generate_synthetic(SyntheticDemo.model_validate(fixture_data()),d)
        assert len(output)==7
        assert all(p.is_file() and p.is_relative_to(d) for p in output)
        assert (d/'app/main.py').is_file()
        assert (d/'tests/test_app.py').is_file()
        assert (d/'data/seed.json').is_file()
        assert not (d/'data/demo.sqlite3').exists()  # database created by demo runtime only


def test_generated_app_passes_its_own_pytest_and_persists_demo_sqlite():
    for d in project(None):
        generate_synthetic(SyntheticDemo.model_validate(fixture_data()),d)
        result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_app.py'],
                              cwd=d,capture_output=True,text=True,timeout=18)
        assert result.returncode==0,result.stdout+result.stderr
        assert '1 passed' in result.stdout
        db=d/'data/demo.sqlite3'
        assert db.is_file()
        with sqlite3.connect(db) as con:
            assert con.execute('select count(*) from items').fetchone()[0]==4


def test_repeat_generation_refuses_overwrite_and_bytes_unchanged():
    for d in project(None):
        model=SyntheticDemo.model_validate(fixture_data())
        generate_synthetic(model,d)
        old=(d/'app/main.py').read_bytes()
        with pytest.raises(ValueError,match='EMPTY'):
            generate_synthetic(model,d)
        assert (d/'app/main.py').read_bytes()==old


def test_nonempty_folder_with_user_file_is_unchanged():
    for d in project(None):
        other=d/'important.txt';other.write_text('keep',encoding='utf-8')
        with pytest.raises(ValueError,match='EMPTY'):
            generate_synthetic(SyntheticDemo.model_validate(fixture_data()),d)
        assert other.read_text()=='keep'
        assert list(d.iterdir())==[other]


@pytest.mark.parametrize('candidate', [
    Path('/mnt/data/astra_contract_unit'), Path('/tmp'), Path('/mnt/data'),
    Path('/tmp/not-astra-name'), Path('/var/tmp/astra-synth-uncreated'),
])
def test_outside_temp_or_non_demo_destinations_blocked(candidate):
    with pytest.raises(ValueError):
        generate_synthetic(SyntheticDemo.model_validate(fixture_data()),candidate)


def test_symlink_destination_refused():
    for d in project(None):
        link=Path(tempfile.gettempdir())/(d.name+'-link')
        try:
            link.symlink_to(d,target_is_directory=True)
            with pytest.raises(ValueError):
                generate_synthetic(SyntheticDemo.model_validate(fixture_data()),link)
            assert not list(d.iterdir())
        finally:
            link.unlink(missing_ok=True)


@pytest.mark.parametrize('change',[
    {'source_kind':'owner_supplied_document'}, {'source_kind':'synthetic_fixture','run_mode':'production'},
    {'schema_version':'0.2'}, {'items':[]}, {'items':None},
])
def test_non_synthetic_or_wrong_mode_rejected(change):
    data=fixture_data();data.update(change)
    with pytest.raises(ValidationError):SyntheticDemo.model_validate(data)


def test_duplicate_ids_are_invalid():
    data=fixture_data();data['items'].append(data['items'][0].copy())
    with pytest.raises(ValidationError,match='duplicate'):SyntheticDemo.model_validate(data)


def test_negative_and_bool_scores_invalid():
    for score in (-1,True,10001,'100'):
        data=fixture_data();data['items'][0]['score']=score
        with pytest.raises(ValidationError):SyntheticDemo.model_validate(data)


def test_extra_properties_rejected():
    data=fixture_data();data['connection_string']='password'
    with pytest.raises(ValidationError):SyntheticDemo.model_validate(data)


def test_generated_code_constant_and_html_never_injects_synthetic_titles():
    for d in project(None):
        data=fixture_data();data['items'][0]['title']='</script><script>alert(1)</script>'
        generate_synthetic(SyntheticDemo.model_validate(data),d)
        js=(d/'app/index.html').read_text()
        py=(d/'app/main.py').read_text()
        seed=(d/'data/seed.json').read_text()
        assert 'alert(1)' not in js and 'alert(1)' not in py
        assert 'alert(1)' in seed and 'textContent' in js
        assert 'INSERT OR IGNORE' in py and 'VALUES(?,?,?,?)' in py


def test_generic_job_demo_emits_valid_fastapi_app():
    for d in project(None):
        data=fixture_data();data['title']='Fictional job roles'
        data['items']=[{'id':'job-one','title':'Data technician','category':'Remote','score':80},
                       {'id':'job-two','title':'Support engineer','category':'Office','score':50}]
        generate_synthetic(SyntheticDemo.model_validate(data),d)
        result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_app.py'],
                              cwd=d,capture_output=True,text=True,timeout=18)
        assert result.returncode==0,result.stdout+result.stderr


def test_command_line_reports_files_and_does_not_override_on_retry(capsys):
    for d in project(None):
        assert main([str(SOURCE),str(d)])==0
        out=capsys.readouterr()
        status=json.loads(out.out)
        assert status['count']==7 and status['status']=='synthetic_files_created'
        assert main([str(SOURCE),str(d)])==1
        assert capsys.readouterr().err.startswith('FAIL:')


def test_existing_contract_keeps_generation_blocked():
    source=ROOT/'fixtures/synthetic_generation_contract_20261018.json'
    c=GenerationContract.model_validate_json(source.read_text())
    assert c.status=='blocked_pending_review'
    assert c.code_generated is False
    assert c.files_written is False
    assert c.approval_verified is False


def test_no_api_write_endpoints_in_generated_example():
    for d in project(None):
        generate_synthetic(SyntheticDemo.model_validate(fixture_data()),d)
        code=(d/'app/main.py').read_text()
        for token in ('@app.post(', '@app.put(', '@app.delete(', 'requests.', 'os.system'):
            assert token not in code
