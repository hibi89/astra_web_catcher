"""Execute the actual generated page controller in a non-browser DOM simulator."""
import json
import shutil
import subprocess
from pathlib import Path
import pytest
from astra_contracts.schema_query_ui import QUERY_UI_HTML

BASE=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('kind',['products','tickets'])
def test_sort_filter_controller_dom(kind):
    node=shutil.which('node')
    if not node:pytest.skip('node not installed: browser interaction remains unverified')
    physical=json.loads((BASE/'fixtures'/f'synthetic_reuse_{kind}_table_20261019.json').read_text(encoding='utf-8'))
    result=subprocess.run([node,str(BASE/'tests/ui_dom_simulation.cjs')],
        input=json.dumps({'html':QUERY_UI_HTML,'table':physical}),text=True,
        capture_output=True,timeout=12)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'UI_DOM_SIM_PASS '+physical['table_name'] in result.stdout
