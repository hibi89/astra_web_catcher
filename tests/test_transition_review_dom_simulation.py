"""Execute the real ledger-panel JS in a small Node DOM sandbox (not Chromium)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from astra_contracts.capture_transition_ledger import build_transition_ledger
from astra_contracts.transition_review_ui import TRANSITION_HTML, build_display_manifest
from tests.test_transition_review_ui import registered_pair

ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/'tests/transition_review_dom_simulation.cjs'

@pytest.mark.skipif(shutil.which('node') is None,reason='Node unavailable')
def test_dom_state_disabled_and_forgery_blocked(registered_pair,tmp_path):
    b,i,p=registered_pair
    manifest=build_display_manifest(build_transition_ledger(b,i,p))
    page=tmp_path/'panel.html';page.write_text(TRANSITION_HTML,encoding='utf-8')
    data=tmp_path/'ledger.json';data.write_text(manifest.model_dump_json(),encoding='utf-8')
    first=subprocess.run(['node',str(RUNNER),str(page),str(data)],capture_output=True,text=True,timeout=10)
    assert first.returncode==0,first.stderr
    assert 'TRANSITION_DOM_DISABLED_PASS' in first.stdout
    raw=manifest.model_dump(mode='json');raw['findings'][0]['enabled']=True
    data.write_text(json.dumps(raw),encoding='utf-8')
    second=subprocess.run(['node',str(RUNNER),str(page),str(data)],capture_output=True,text=True,timeout=10)
    assert second.returncode==0,second.stderr
    assert 'FORGED_TRANSITION_BLOCKED' in second.stdout
