import pytest
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.ps import (
    forbid_re_delimiters_inside_groups,
    convert_inventory_processes,
    validate_process_discovery_descr_option,
)
from cmk.gui.plugins.wato.check_parameters.cpu_utilization import transform_cpu_iowait


@pytest.mark.parametrize('pattern', ["(test)$", 'foo\\b', '^bar', '\\bfoo\\b', '(a)\\b'])
def test_validate_ps_allowed_regex(pattern):
    assert forbid_re_delimiters_inside_groups(pattern, '') is None


@pytest.mark.parametrize('pattern', ["(test$)", '(foo\\b)', '(^bar)', '(\\bfoo\\b)'])
def test_validate_ps_forbidden_regex(pattern):
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, '')


@pytest.mark.parametrize('description', ["%s%5"])
def test_validate_process_discovery_descr_option(description):
    with pytest.raises(MKUserError):
        validate_process_discovery_descr_option(description, '')


@pytest.mark.parametrize('params, result', [
    (
        (10, 20),
        {
            'iowait': (10, 20)
        },
    ),
    ({}, {}),
    (
        {
            'util': (50, 60)
        },
        {
            'util': (50, 60)
        },
    ),
])
def test_transform_cpu_iowait(params, result):
    assert transform_cpu_iowait(params) == result


@pytest.mark.parametrize('params, result', [
    ({}, {
        'default_params': {
            "cpu_rescale_max": None
        }
    }),
    ({
        'levels': (1, 1, 50, 50),
    }, {
        'default_params': {
            'levels': (1, 1, 50, 50),
            "cpu_rescale_max": None,
        },
    }),
    ({
        'user': False,
        'default_params': {
            'virtual_levels': (50, 100),
        }
    }, {
        'user': False,
        'default_params': {
            'virtual_levels': (50, 100),
            "cpu_rescale_max": None,
        }
    }),
    ({
        'default_params': {
            'cpu_rescale_max': True
        },
        'match': '/usr/lib/firefox/firefox',
        'descr': 'firefox',
        'user': False
    }, {
        'default_params': {
            'cpu_rescale_max': True
        },
        'match': '/usr/lib/firefox/firefox',
        'descr': 'firefox',
        'user': False
    }),
])
def test_convert_inventory_process(params, result):
    assert convert_inventory_processes(params) == result
