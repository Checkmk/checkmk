import pytest

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_cpu"


@pytest.mark.parametrize("info, result_expected", [
    ([[u'doesnt matter', u'doesent matter'], [u'doesnt matter']
     ], [(None, "alcatel_cpu_default_levels")]),
])
def test_inventory_function(check_manager, info, result_expected):
    check = check_manager.get_check(CHECK_NAME)
    result = check.run_discovery(info)
    result = [r for r in result]
    assert result == result_expected


@pytest.mark.parametrize("parameters, info, state_expected, infotext_expected, perfdata_expected", [
    ((30, 40), [[u'29']], 0, 'total: 29.0%', [('util', 29, 30, 40, 0, 100)]),
    ((30, 40), [[u'31']
               ], 1, 'total: 31.0% (warn/crit at 30.0%/40.0%)', [('util', 31, 30, 40, 0, 100)]),
    ((30, 40), [[u'41']
               ], 2, 'total: 41.0% (warn/crit at 30.0%/40.0%)', [('util', 41, 30, 40, 0, 100)]),
])
def test_check_function(check_manager, parameters, info, state_expected, infotext_expected,
                        perfdata_expected):
    """
    Verifies if check function asserts warn and crit CPU levels.
    """
    check = check_manager.get_check(CHECK_NAME)
    item = None
    state, infotext, perfdata = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext == infotext_expected
    assert perfdata == perfdata_expected
