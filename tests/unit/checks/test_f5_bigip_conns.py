import pytest

pytestmark = pytest.mark.checks

from cmk.base.check_api import MKGeneralException
from checktestlib import CheckResult, assertCheckResultsEqual


@pytest.mark.parametrize("config, result", [
    ({}, (None, None, None, None)),
    ({
        "connections_rate": (2, 5),
        "connections_rate_lower": (1, 0),
    }, (2, 5, 1, 0)),
    ({
        "connections_rate_lower": (1, 0),
    }, (None, None, 1, 0)),
    ({
        "connections_rate": (2, 5),
    }, (2, 5, None, None)),
    ({
        'connections_rate': {
            'levels_upper': ('absolute', (0.0, 0.0)),
            'levels_lower': ('stdev', (2.0, 4.0)),
            'period': 'wday',
            'horizon': 90
        },
    }, {
        'levels_upper': ('absolute', (0.0, 0.0)),
        'levels_lower': ('stdev', (2.0, 4.0)),
        'period': 'wday',
        'horizon': 90
    }),
])
def test_get_conn_rate_params(check_manager, config, result):
    check = check_manager.get_check("f5_bigip_conns")
    assert check.context["get_conn_rate_params"](config) == result


@pytest.mark.parametrize("config, exception_msg", [({
    'connections_rate': {
        'levels_upper': ('absolute', (0.0, 0.0)),
        'levels_lower': ('stdev', (2.0, 4.0)),
        'period': 'wday',
        'horizon': 90
    },
    "connections_rate_lower": (1, 0),
}, ("Can't configure minimum connections per second when the maximum "
    "connections per second is setup in predictive levels. Please use the given "
    "lower bound specified in the maximum connections, or set maximum "
    "connections to use fixed levels."))])
def test_get_conn_rate_params_exception(check_manager, config, exception_msg):
    check = check_manager.get_check("f5_bigip_conns")
    with pytest.raises(ValueError, match=exception_msg):
        check.context["get_conn_rate_params"](config)
