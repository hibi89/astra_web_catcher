"""Execute the real review-widget JS in a minimal DOM sandbox, not Chromium."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from astra_contracts.mapping_review_ui import REVIEW_HTML, build_review_manifest
from astra_contracts.observed_ui_mapping import build_ui_mapping
from tests.test_mapping_review_ui import inputs, blocked_report

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'tests/mapping_review_dom_simulation.cjs'


@pytest.mark.skipif(shutil.which('node') is None,reason='Node.js not installed')
@pytest.mark.parametrize('kind',['products','tickets'])
def test_review_ui_dom_never_activates(kind):
    b,d,t,p=inputs(kind)
    manifest=build_review_manifest(build_ui_mapping(b,d,t,p,ROOT/'fixtures'),t,blocked_report())
    with tempfile.TemporaryDirectory(prefix='astra-review-js-') as d:
        root=Path(d)
        page=root/'page.html';page.write_text(REVIEW_HTML,encoding='utf-8')
        data=root/'manifest.json';data.write_text(manifest.model_dump_json(),encoding='utf-8')
        result=subprocess.run(['node',str(RUNNER),str(page),str(data)],capture_output=True,text=True,timeout=10)
        assert result.returncode==0,result.stderr
        assert 'REVIEW_ONLY_DOM_PASS' in result.stdout
        raw=manifest.model_dump(mode='json');raw['items'][0]['enabled']=True
        data.write_text(json.dumps(raw),encoding='utf-8')
        result=subprocess.run(['node',str(RUNNER),str(page),str(data)],capture_output=True,text=True,timeout=10)
        assert result.returncode==0,result.stderr
        assert 'DISABLED_TAMPER_BLOCKED' in result.stdout
