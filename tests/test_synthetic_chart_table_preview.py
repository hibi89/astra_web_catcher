"""Offline preview contract: real UI markup, fail-closed data, no asserted owner permissions."""
from __future__ import annotations
import copy
import math
from pathlib import Path
import pytest

from astra_contracts.synthetic_chart_table_preview import render_preview, main


def fixture():
    return {'source_kind':'synthetic_fixture','dataset_id':'safe_example',
            'columns':[{'name':'entity','kind':'string'}, {'name':'period','kind':'string'},
                       {'name':'measure','kind':'number'}, {'name':'method','kind':'string'}],
            'proposed_bindings':{'entity_identifier':'entity','time_period':'period',
                                 'numeric_measure':'measure','aggregation_semantics':'method'}}


def rows():
    return [ {'entity':'Alpha','period':'2024','measure':12.5,'method':'synthetic_sample'},
             {'entity':'Alpha','period':'2025','measure':16,'method':'synthetic_sample'},
             {'entity':'Beta','period':'2024','measure':8,'method':'synthetic_sample'},
             {'entity':'Beta','period':'2025','measure':10,'method':'synthetic_sample'} ]


def test_real_chart_and_table_have_equal_row_count_and_single_state_switch():
    markup = render_preview(fixture(),rows())
    assert '<svg ' in markup and '<circle ' in markup and '<line ' in markup
    assert '<tbody>' in markup and markup.count('<tr>') == 5  # header plus 4 data rows
    assert 'show-table' in markup and "tableButton.addEventListener('click'" in markup
    assert 'id="table-view"' in markup and 'hidden>' in markup
    assert 'REVIEW ONLY' in markup and 'unapproved' in markup
    assert 'This is not an OWID data reproduction' in markup


def test_entity_is_escaped_and_not_executable():
    x = rows(); x[0]['entity'] = '<script>alert(1)</script>'
    # unique entity/period ensures this is an independent series; only escaped text allowed
    markup = render_preview(fixture(), x)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in markup
    assert '<script>alert(1)</script>' not in markup


def test_missing_mapping_fails():
    s = fixture(); del s['proposed_bindings']['numeric_measure']
    with pytest.raises(ValueError,match='missing or incompatible'):
        render_preview(s,rows())


def test_invalid_type_mapping_fails():
    s = fixture(); s['columns'][2]['kind'] = 'boolean'
    with pytest.raises(ValueError,match='missing or incompatible'):
        render_preview(s,rows())


def test_two_roles_to_one_column_fails():
    s=fixture(); s['proposed_bindings']['aggregation_semantics']='entity'
    with pytest.raises(ValueError,match='distinct columns'):
        render_preview(s,rows())


@pytest.mark.parametrize('alter', ['extra_key','missing_key','bool_number','nan','infinity',
                                    'duplicated_pair','mixed_method','invalid_period','mixed_granularity',
                                    'empty_string','wrong_integer_type','overflow','not_list'])
def test_malformed_or_semantically_ambiguous_rows_fail(alter):
    s=fixture(); r=rows()
    if alter == 'extra_key': r[0]['api_key']='no'
    if alter == 'missing_key': del r[0]['entity']
    if alter == 'bool_number': r[0]['measure']=True
    if alter == 'nan': r[0]['measure']=float('nan')
    if alter == 'infinity': r[0]['measure']=float('inf')
    if alter == 'duplicated_pair': r[1] = copy.deepcopy(r[0])
    if alter == 'mixed_method': r[0]['method']='other_metric'
    if alter == 'invalid_period': r[0]['period']='2024-14'
    if alter == 'mixed_granularity': r[0]['period']='2024-01'
    if alter == 'empty_string': r[0]['entity']=' '
    if alter == 'wrong_integer_type': s['columns'][2]['kind']='integer'; r[0]['measure']=12.5
    if alter == 'overflow': r[0]['measure']=1e30
    if alter == 'not_list': r={'not':'a list'}
    with pytest.raises(ValueError):
        render_preview(s,r)


def test_no_rows_fails():
    with pytest.raises(ValueError,match='1..240'):
        render_preview(fixture(),[])


def test_exceeds_limits_fails():
    r=[{'entity':'E'+str(i),'period':'2024','measure':1,'method':'sample'} for i in range(11)]
    with pytest.raises(ValueError,match='10 entities'):
        render_preview(fixture(),r)


def test_valid_monthly_data():
    r=rows(); r[0]['period']='2024-01';r[1]['period']='2024-02';r[2]['period']='2024-01';r[3]['period']='2024-02'
    markup=render_preview(fixture(),r)
    assert '2024-01' in markup and '2024-02' in markup


def test_missing_proof_archive_fails_closed(tmp_path):
    with pytest.raises(ValueError,match='regular ZIP file required'):
        render_preview(fixture(),rows(),archive=tmp_path/'missing.zip')


def test_forged_archive_fails_closed(tmp_path):
    p=tmp_path/'fake.zip';p.write_bytes(b'fake')
    with pytest.raises(ValueError,match='pinned ZIP SHA mismatch'):
        render_preview(fixture(),rows(),archive=p)


def test_cli_outputs_only_explicit_new_file(tmp_path):
    import json
    schema_path,rows_path,output = [tmp_path/name for name in ('schema.json','rows.json','preview.html')]
    schema_path.write_text(json.dumps(fixture()),encoding='utf-8')
    rows_path.write_text(json.dumps(rows()),encoding='utf-8')
    args=['--fixture',str(schema_path),'--rows',str(rows_path),'--output',str(output)]
    assert main(args) == 0
    assert output.read_text(encoding='utf-8').startswith('<!doctype html>')
    assert main(args) == 1  # no overwrite


def test_proof_linked_with_exact_archive_when_present():
    archive=Path('/mnt/data/p4-owid-evidence.zip')
    if not archive.is_file():
        pytest.skip('Original pinned OWID evidence archive not provided; no fabricated substitute')
    markup=render_preview(fixture(),rows(),archive=archive)
    assert 'Pinned public UI evidence integrity verified locally' in markup
    assert 'Metric calculation: unverified' in markup
