import copy
import pytest
from astra_contracts.synthetic_timeseries_review import review


def sample():
    return {'source_kind': 'synthetic_fixture', 'dataset_id': 'demo_series',
            'columns': [{'name': 'entity', 'kind': 'string'}, {'name': 'period', 'kind': 'string'},
                        {'name': 'value', 'kind': 'number'}, {'name': 'method', 'kind': 'string'}],
            'proposed_bindings': {'entity_identifier': 'entity', 'time_period': 'period',
                                  'numeric_measure': 'value', 'aggregation_semantics': 'method'}}


def test_compatible_but_never_approved():
    result = review(sample())
    assert result['missing_or_incompatible'] == []
    assert all(v['status'] == 'structurally_compatible_unapproved' for v in result['findings'].values())
    assert not any(result[k] for k in ('semantic_approval_verified', 'owner_database_access_authorized',
                                      'code_generation_authorized', 'deployment_authorized'))


def test_missing_role():
    x = sample(); del x['proposed_bindings']['time_period']
    assert review(x)['missing_or_incompatible'] == ['time_period']


def test_missing_column():
    x = sample(); x['proposed_bindings']['numeric_measure'] = 'missing'
    assert review(x)['findings']['numeric_measure']['status'] == 'missing_column'


def test_type_mismatch():
    x = sample(); x['columns'][2]['kind'] = 'boolean'
    assert review(x)['findings']['numeric_measure']['status'] == 'type_mismatch'


def test_integer_measure():
    x = sample(); x['columns'][2]['kind'] = 'integer'
    assert review(x)['findings']['numeric_measure']['status'] == 'structurally_compatible_unapproved'


@pytest.mark.parametrize('case', ['duplicate', 'extra', 'owner', 'role', 'invalid_name', 'nested'])
def test_invalid_fixture_rejected(case):
    x = sample()
    if case == 'duplicate': x['columns'].append(copy.deepcopy(x['columns'][0]))
    if case == 'extra': x['credentials'] = 'secret'
    if case == 'owner': x['source_kind'] = 'owner_supplied_document'
    if case == 'role': x['proposed_bindings']['invented_role'] = 'value'
    if case == 'invalid_name': x['columns'][0]['name'] = '../escape'
    if case == 'nested': x['proposed_bindings']['time_period'] = {'bad': 'value'}
    with pytest.raises(ValueError):
        review(x)
