import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, item_expected, data_expected", [
    ([[u'29', u'0']], 'Board', {}),
    ([[u'0', u'29']], 'CPU', {}),
])
def test_inventory_function(check_manager, info, item_expected, data_expected):
    """
    Verifies if the item is detected corresponding to info content.
    """
    check = check_manager.get_check("alcatel_temp")
    result = check.run_discovery(info)
    result = [r for r in result]
    assert result[0][0] == item_expected
    assert result[0][1] == data_expected


@pytest.mark.parametrize(
    "parameters, item, info, state_expected, infotext_expected, perfdata_expected", [
        ((30, 40), u'Slot 1 Board', [[u'29', u'0']], 0, '29', [('temp', 29, 30, 40)]),
        ((30, 40), u'Slot 1 Board', [[u'31', u'0']], 1, '31', [('temp', 31, 30, 40)]),
        ((30, 40), u'Slot 1 Board', [[u'41', u'0']], 2, '41', [('temp', 41, 30, 40)]),
        ((30, 40), u'Slot 1 CPU', [[u'0', u'29']], 0, '29', [('temp', 29, 30, 40)]),
        ((30, 40), u'Slot 1 CPU', [[u'0', u'31']], 1, '31', [('temp', 31, 30, 40)]),
        ((30, 40), u'Slot 1 CPU', [[u'0', u'41']], 2, '41', [('temp', 41, 30, 40)]),
    ])
def test_check_function(check_manager, parameters, item, info, state_expected, infotext_expected,
                        perfdata_expected):
    """
    Verifies if check function asserts warn and crit Board and CPU temperature levels.
    """
    check = check_manager.get_check("alcatel_temp")
    state, infotext, perfdata = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext_expected in infotext
    assert perfdata == perfdata_expected
