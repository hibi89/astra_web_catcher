"""Physical synthetic schema reuse must not turn inferred original behavior into truth."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import OwnedSchemaDeclaration
from astra_contracts.feature_acceptance_adapter import FeatureCase, _expected_from_fixture
from astra_contracts.generation_contract import GenerationRequest, fingerprint
from astra_contracts.observation import ObservationBundle
from astra_contracts.schema_reuse_adapter import (
    AlternateSyntheticTable, SchemaAcceptanceCases, SchemaReuseResult,
    normalize_table, run_schema_reuse, main,
)
from astra_contracts.synthetic_generator import SyntheticDemo, SyntheticRow

FIX = Path(__file__).resolve().parents[1] / 'fixtures'


def samples(name):
    bundle=ObservationBundle.model_validate_json((FIX/'synthetic_manual_filter_observation_20261019.json').read_text())
    schema=OwnedSchemaDeclaration.model_validate_json((FIX/'synthetic_manual_filter_schema_20261019.json').read_text())
    request=GenerationRequest.model_validate_json((FIX/'synthetic_generation_request_20261018.json').read_text())
    table=AlternateSyntheticTable.model_validate_json((FIX/f'synthetic_reuse_{name}_table_20261019.json').read_text())
    cases=SchemaAcceptanceCases.model_validate_json((FIX/f'synthetic_reuse_{name}_cases_20261019.json').read_text())
    return bundle,schema,request,table,cases


@pytest.mark.parametrize('name,expected_rows,expected_cases',[('products',3,6),('tickets',4,7)])
def test_normalize_and_execute_real_api(name,expected_rows,expected_cases):
    bundle,schema,request,table,cases=samples(name)
    before=(fingerprint(bundle),fingerprint(schema),fingerprint(table),fingerprint(cases))
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        out=Path(folder)
        result=run_schema_reuse(bundle,FIX,schema,request,table,cases,out)
        assert result.status=='multi_schema_synthetic_only_passed'
        assert result.normalized_row_count==expected_rows
        assert result.acceptance_cases_passed==expected_cases
        assert result.source_illustrations_passed==1
        assert len(result.physical_fields)==4
        assert not any([result.original_site_behavior_verified,result.customer_database_accessed,
                        result.code_generation_authorized,result.deployment_authorized])
        stored=SchemaReuseResult.model_validate_json((out/'data/schema_reuse_report.json').read_text())
        assert stored==result
        assert not (out/'data/approved.json').exists()
        assert len(list(out.rglob('*.sqlite3')))>0
    assert (fingerprint(bundle),fingerprint(schema),fingerprint(table),fingerprint(cases))==before


def test_same_logical_features_from_physically_different_tables():
    a=normalize_table(samples('products')[3])
    b=normalize_table(samples('tickets')[3])
    assert a.source_kind==b.source_kind=='synthetic_fixture'
    assert len(a.items)==3 and len(b.items)==4
    assert set(SyntheticRow.model_fields)=={'id','title','category','score'}
    assert set(SyntheticRow.model_fields)=={'id','title','category','score'}
    assert a.items[0].id.startswith('prod-') and b.items[0].id.startswith('ticket-')
    assert a.model_dump()!=b.model_dump()


def test_order_of_source_mapping_does_not_matter():
    t=samples('tickets')[3]
    raw=t.model_dump(mode='json'); raw['bindings'].reverse()
    assert normalize_table(AlternateSyntheticTable.model_validate(raw))==normalize_table(t)


def test_explicit_expected_ids_are_not_self_validating():
    table=samples('products')[3]
    cases=samples('products')[4]
    demo=normalize_table(table)
    assert any(_expected_from_fixture(c,demo)[1]!=[] for c in cases.cases)
    assert len([c for c in cases.cases if c.relationship=='source_feature_illustration'])==1


@pytest.mark.parametrize('edit',[
    lambda v:v['bindings'].pop(),
    lambda v:v['bindings'].append(v['bindings'][0]),
    lambda v:v['bindings'].__setitem__(1,copy.deepcopy(v['bindings'][0])),
    lambda v:v['bindings'][1].__setitem__('source_field',v['bindings'][0]['source_field']),
    lambda v:v['bindings'][0].__setitem__('source_field','unknown_source'),
    lambda v:v.__setitem__('original_site_behavior_verified',True),
    lambda v:v.__setitem__('customer_database_connected',True),
    lambda v:v.__setitem__('schema_mapping_approved',True),
    lambda v:v.__setitem__('source_kind','customer_database'),
    lambda v:v.__setitem__('run_mode','production'),
    lambda v:v.__setitem__('table_name','real; DROP TABLE users'),
    lambda v:v['rows'][0].__setitem__('secret_field','should not leak'),
    lambda v:v['rows'][0].pop('sku'),
    lambda v:v['rows'][0].__setitem__('popularity',True),
    lambda v:v['rows'][0].__setitem__('popularity','90'),
    lambda v:v['rows'][0].__setitem__('sku','../../outside'),
    lambda v:v['rows'][0].__setitem__('display_name','x'*257),
])
def test_bad_table_rejected(edit):
    raw=samples('products')[3].model_dump(mode='json')
    edit(raw)
    with pytest.raises((ValueError,ValidationError)):
        table=AlternateSyntheticTable.model_validate(raw)
        normalize_table(table)


def test_boolean_score_does_not_coerce_to_int():
    data=samples('tickets')[3].model_dump(mode='json')
    data['rows'][0]['priority']=False
    with pytest.raises((ValueError,ValidationError)):
        normalize_table(AlternateSyntheticTable.model_validate(data))


def test_duplicate_normalized_ids_rejected():
    data=samples('products')[3].model_dump(mode='json')
    data['rows'][1]['sku']=data['rows'][0]['sku']
    with pytest.raises(ValidationError,match='duplicate'):
        normalize_table(AlternateSyntheticTable.model_validate(data))


def test_source_field_types_strict():
    data=samples('tickets')[3].model_dump(mode='json')
    data['rows'][1]['lane']=4
    with pytest.raises(ValueError,match='strings'):
        normalize_table(AlternateSyntheticTable.model_validate(data))


@pytest.mark.parametrize('patch',[
    lambda v:v.__setitem__('table_sha256','0'*64),
    lambda v:v.__setitem__('original_site_verified',True),
    lambda v:v.__setitem__('production_authorized',True),
    lambda v:v.__setitem__('scope','customer_database'),
    lambda v:v.__setitem__('unknown_approval',True),
    lambda v:v['cases'][0].__setitem__('expected_ids',['wrong-id']),
    lambda v:v['cases'][0].__setitem__('source_observation_id','foreign'),
    lambda v:v['cases'][0].__setitem__('feature','detail'),
])
def test_bad_cases_block_before_writing(patch):
    bundle,schema,request,table,cases=samples('products')
    raw=cases.model_dump(mode='json'); patch(raw)
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        out=Path(folder)
        with pytest.raises((ValueError,ValidationError)):
            cases2=SchemaAcceptanceCases.model_validate(raw)
            run_schema_reuse(bundle,FIX,schema,request,table,cases2,out)
        assert not list(out.iterdir())


def test_stale_source_fixture_rejected_before_write():
    bundle,schema,request,table,cases=samples('tickets')
    data=table.model_dump(mode='json')
    data['rows'][0]['priority']=40
    mutated=AlternateSyntheticTable.model_validate(data)
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        with pytest.raises(ValueError,match='stale'):
            run_schema_reuse(bundle,FIX,schema,request,mutated,cases,Path(folder))
        assert not list(Path(folder).iterdir())


def test_unknown_or_wrong_feature_reference_rejected():
    bundle,schema,request,table,cases=samples('products')
    raw=cases.model_dump(mode='json');raw['cases'][0]['feature']='search';raw['cases'][0]['category']=None;raw['cases'][0]['q']='Blue'
    raw['cases'][0]['expected_ids']=['prod-cobalt']
    changed=SchemaAcceptanceCases.model_validate(raw)
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        with pytest.raises(ValueError,match='source illustration'):
            run_schema_reuse(bundle,FIX,schema,request,table,changed,Path(folder))
        assert not list(Path(folder).iterdir())


def test_nonempty_temp_destination_preserved():
    bundle,schema,request,table,cases=samples('products')
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        marker=Path(folder)/'keep.txt'; marker.write_text('NEVER TOUCH')
        with pytest.raises(ValueError,match='EMPTY'):
            run_schema_reuse(bundle,FIX,schema,request,table,cases,Path(folder))
        assert marker.read_text()=='NEVER TOUCH'


def test_not_temp_destination_rejected(tmp_path):
    bundle,schema,request,table,cases=samples('products')
    with pytest.raises(ValueError,match='EMPTY'):
        run_schema_reuse(bundle,FIX,schema,request,table,cases,tmp_path)
    assert not list(tmp_path.iterdir())


def test_owner_supplied_schema_rejected_before_write():
    bundle,schema,request,table,cases=samples('products')
    raw=schema.model_dump(mode='json');raw['source_kind']='owner_supplied_document'
    owner=OwnedSchemaDeclaration.model_validate(raw)
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        with pytest.raises(ValueError,match='synthetic'):
            run_schema_reuse(bundle,FIX,owner,request,table,cases,Path(folder))
        assert not list(Path(folder).iterdir())


def test_cli_two_different_schemas(capsys):
    for name in ('products','tickets'):
        with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
            argv=[str(FIX/'synthetic_manual_filter_observation_20261019.json'),str(FIX),
                str(FIX/'synthetic_manual_filter_schema_20261019.json'),
                str(FIX/'synthetic_generation_request_20261018.json'),
                str(FIX/f'synthetic_reuse_{name}_table_20261019.json'),
                str(FIX/f'synthetic_reuse_{name}_cases_20261019.json'),folder]
            assert main(argv)==0
            msg=json.loads(capsys.readouterr().out)
            assert msg['status']=='multi_schema_synthetic_only_passed'
            assert msg['acceptance_cases_passed'] in {6,7}


def test_cli_rejects_corrupt_source_without_writes(tmp_path,capsys):
    table_path=tmp_path/'invalid.json'
    table_path.write_text('{ broken JSON')
    with tempfile.TemporaryDirectory(prefix='astra-synth-reuse-') as folder:
        argv=[str(FIX/'synthetic_manual_filter_observation_20261019.json'),str(FIX),
            str(FIX/'synthetic_manual_filter_schema_20261019.json'),
            str(FIX/'synthetic_generation_request_20261018.json'),str(table_path),
            str(FIX/'synthetic_reuse_products_cases_20261019.json'),folder]
        assert main(argv)==1
        assert 'FAIL' in capsys.readouterr().err
        assert not list(Path(folder).iterdir())
