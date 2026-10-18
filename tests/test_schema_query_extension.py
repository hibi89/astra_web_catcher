"""Sorting and typed filtering operate solely on explicitly declared synthetic columns."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from astra_contracts.schema_query_extension import (
    QueryPlan, QueryReport, create_query_app, main, select_rows, verify_query_plan,
)
from astra_contracts.schema_reuse_adapter import AlternateSyntheticTable
from astra_contracts.generation_contract import fingerprint

F = Path(__file__).resolve().parents[1] / 'fixtures'


def fixtures(name):
    table = AlternateSyntheticTable.model_validate_json((F/f'synthetic_reuse_{name}_table_20261019.json').read_text(encoding='utf-8'))
    plan = QueryPlan.model_validate_json((F/f'synthetic_reuse_{name}_query_cases_20261019.json').read_text(encoding='utf-8'))
    return table, plan


@pytest.mark.parametrize('name,count', [('products', 9), ('tickets', 9)])
def test_full_real_asgi_query_contract(name, count):
    table, plan=fixtures(name)
    before=(fingerprint(table), fingerprint(plan))
    result=verify_query_plan(table,plan)
    assert isinstance(result, QueryReport)
    assert result.pass_count==count
    assert result.status=='synthetic_query_contract_passed'
    assert result.physical_sortable_fields==sorted(x.source_field for x in table.bindings)
    assert not any([result.original_site_behavior_verified, result.customer_database_accessed,
                    result.code_generation_authorized,result.deployment_authorized])
    assert (fingerprint(table),fingerprint(plan))==before


def test_products_hand_authored_oracles_match_expected_ids():
    _,plan=fixtures('products')
    cases={c.id:c.expected_ids for c in plan.cases}
    assert cases['score-desc']==['prod-shimmer','prod-cobalt','prod-rose']
    assert cases['score-asc']==['prod-rose','prod-cobalt','prod-shimmer']
    assert cases['family-colors']==['prod-cobalt','prod-rose']
    assert cases['numeric-score']==['prod-cobalt']
    assert cases['limit-two']==['prod-shimmer','prod-cobalt']
    assert cases['case-sensitive']==[]


def test_tickets_hand_authored_oracles_and_stable_sort():
    _,plan=fixtures('tickets')
    cases={c.id:c.expected_ids for c in plan.cases}
    assert cases['priority-desc']==['ticket-payment','ticket-login','ticket-other','ticket-closed']
    assert cases['priority-asc']==['ticket-closed','ticket-login','ticket-other','ticket-payment']
    assert cases['lane-open']==['ticket-payment','ticket-login','ticket-other']
    assert cases['score-45']==['ticket-other','ticket-login']
    assert cases['mixed-case']==[]
    assert cases['title-sort']==['ticket-login','ticket-other','ticket-payment','ticket-closed']


@pytest.mark.parametrize('name',[ 'products','tickets'])
def test_response_preserves_physical_names_and_typed_values(name):
    table,_=fixtures(name)
    numeric=next(x.source_field for x in table.bindings if x.logical_field=='score')
    all_cols={b.source_field for b in table.bindings}
    with TestClient(create_query_app(table)) as client:
        rsp=client.get('/api/rows',params={'sort_by':numeric,'direction':'desc'})
        assert rsp.status_code==200
        data=rsp.json()
        assert data['synthetic'] and not data['original_site_behavior_verified']
        assert data['source_kind']=='synthetic_fixture'
        assert all(set(row)==all_cols and type(row[numeric]) is int for row in data['items'])
        assert all(data['items'][i][numeric]>=data['items'][i+1][numeric] for i in range(len(data['items'])-1))
        assert client.post('/api/rows').status_code==405


@pytest.mark.parametrize('name',[ 'products','tickets'])
def test_unknown_sort_filter_columns_are_not_inferred(name):
    table,_=fixtures(name)
    sortable=table.bindings[0].source_field
    with TestClient(create_query_app(table)) as client:
        for bad in ('nonexistent','score','id','__class__','popularity; DROP TABLE a'):
            # Physical-only names; if an alias happens to exist, it must be bound.
            if bad in [b.source_field for b in table.bindings]:
                continue
            assert client.get('/api/rows',params={'sort_by':bad}).status_code==422
            assert client.get('/api/rows',params={'sort_by':sortable,'filter_by':bad,'filter_value':'x'}).status_code==422


def test_invalid_numeric_filter_rejected_not_coerced():
    table,_=fixtures('tickets')
    with TestClient(create_query_app(table)) as client:
        for bad in ('45.0','-1','NaN','True','1e2','999999','45 OR 1=1','+45','045',''):
            rsp=client.get('/api/rows',params={'sort_by':'priority','filter_by':'priority','filter_value':bad})
            assert rsp.status_code==422, bad
        rsp=client.get('/api/rows',params={'sort_by':'priority','filter_by':'priority','filter_value':'45'})
        assert rsp.status_code==200
        assert len(rsp.json()['items'])==2


def test_injection_like_search_is_a_literal_value():
    table,_=fixtures('products')
    with TestClient(create_query_app(table)) as client:
        for v in ("' OR 1=1 --", '%', 'colors;DROP TABLE products'):
            resp=client.get('/api/rows',params={'sort_by':'sku','filter_by':'family','filter_value':v})
            assert resp.status_code==200
            assert resp.json()['items']==[]
        assert [i['sku'] for i in client.get('/api/rows',params={
            'sort_by':'sku','filter_by':'display_name','filter_value':'Blue Gel %'}).json()['items']]==['prod-cobalt']


def test_missing_pair_bad_direction_limit_validation():
    table,_=fixtures('products')
    with TestClient(create_query_app(table)) as client:
        for params in (
            {'sort_by':'sku','filter_by':'family'},
            {'sort_by':'sku','filter_value':'colors'},
            {'sort_by':'sku','direction':'sideways'},
            {'sort_by':'sku','limit':'0'},
            {'sort_by':'sku','limit':'101'},
            {'sort_by':'sku','limit':'bogus'},
            {},
        ):
            assert client.get('/api/rows',params=params).status_code==422


def test_same_fixture_data_never_mutated():
    table,_=fixtures('tickets')
    initial=fingerprint(table)
    for _ in range(4):
        select_rows(table,sort_by='priority',direction='desc',filter_by='lane',filter_value='Open')
    assert fingerprint(table)==initial


def test_tiebreak_id_asc_even_descending_score():
    table,_=fixtures('tickets')
    rows=select_rows(table,sort_by='priority',direction='desc')
    same=[row['ticket_key'] for row in rows if row['priority']==45]
    assert same==['ticket-login','ticket-other']


def test_pure_adapter_rejects_boolean_limit():
    table,_=fixtures('products')
    with pytest.raises(ValueError):
        select_rows(table,sort_by='sku',limit=True)


@pytest.mark.parametrize('change',[ 
    lambda x:x.__setitem__('source_table_sha256','0'*64),
    lambda x:x.__setitem__('original_site_behavior_verified',True),
    lambda x:x.__setitem__('user_database_access_authorized',True),
    lambda x:x.__setitem__('deployment_authorized',True),
    lambda x:x['cases'][0].__setitem__('sort_by','unknown_column'),
    lambda x:x['cases'][0].__setitem__('expected_ids',['bad-id']),
    lambda x:x['cases'][0].__setitem__('limit',0),
    lambda x:x['cases'][0].__setitem__('direction','invalid'),
    lambda x:x['cases'][0].__setitem__('filter_by','family'),
    lambda x:x['cases'][0].__setitem__('filter_value','colors'),
    lambda x:x['cases'][0].__setitem__('original_site_behavior_verified',True),
    lambda x:x['cases'].append(copy.deepcopy(x['cases'][0])),
])
def test_bad_plan_rejected(change):
    table,plan=fixtures('products')
    data=plan.model_dump(mode='json')
    change(data)
    with pytest.raises((ValidationError,ValueError)):
        verify_query_plan(table,QueryPlan.model_validate(data))


def test_reused_cases_rejected_against_other_schema():
    tickets,_=fixtures('tickets')
    _,products_plan=fixtures('products')
    with pytest.raises(ValueError,match='stale'):
        verify_query_plan(tickets,products_plan)


def test_partial_case_coverage_rejected():
    table,plan=fixtures('tickets')
    data=plan.model_dump(mode='json')
    data['cases']=[c for c in data['cases'] if c['direction']=='asc']
    with pytest.raises(ValidationError,match='descending'):
        QueryPlan.model_validate(data)


def test_cli_report_and_no_file_mutation(tmp_path,capsys):
    table,plan=fixtures('products')
    table_file=tmp_path/'products.json';plan_file=tmp_path/'query.json'
    table_file.write_text(table.model_dump_json(),encoding='utf-8')
    plan_file.write_text(plan.model_dump_json(),encoding='utf-8')
    old=(table_file.read_bytes(),plan_file.read_bytes())
    assert main([str(table_file),str(plan_file)])==0
    report=json.loads(capsys.readouterr().out)
    assert report['pass_count']==9
    assert report['status']=='synthetic_query_contract_passed'
    assert not report['customer_database_accessed']
    assert (table_file.read_bytes(),plan_file.read_bytes())==old
    assert set(tmp_path.iterdir())=={table_file,plan_file}


def test_cli_wrong_source_returns_nonzero(tmp_path,capsys):
    table,plan=fixtures('products')
    a=tmp_path/'source.json';b=tmp_path/'cases.json'
    a.write_text(table.model_dump_json())
    raw=plan.model_dump(mode='json');raw['source_table_sha256']='0'*64
    b.write_text(json.dumps(raw))
    assert main([str(a),str(b)])==1
    assert 'FAIL' in capsys.readouterr().err
