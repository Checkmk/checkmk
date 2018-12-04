import pytest

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_power"


# info: oid end, status, device type, power type
@pytest.mark.parametrize(
    "info, result_expected",
    [
        ([[u'1', u'0', u'0x35000001', u'0']], [('1', None)
                                              ]),  # item is oid in case of proper device type
        ([[u'1', u'0', u'0x45000002', u'0']], [('1', None)
                                              ]),  # item is oid in case of proper device type
        ([[u'1', u'0', u'0x45000004', u'0']], [('1', None)
                                              ]),  # item is oid in case of proper device type
        ([[u'1', u'0', u'0x45000008', u'0']], [('1', None)
                                              ]),  # item is oid in case of proper device type
        ([[u'1', u'0', u'0x45000009', u'0']], [('1', None)
                                              ]),  # item is oid in case of proper device type
        ([[u'1', u'0', u'0', u'0']],
         []),  # no item is oid in case of inproper device type and inproper power type
        ([[u'1', u'0', u'0', u'1']], [('1', None)]),  # item is oid in case of proper power type
    ])
def test_inventory_function(check_manager, info, result_expected):
    check = check_manager.get_check(CHECK_NAME)
    result = check.run_discovery(info)
    result = [r for r in result]
    assert result == result_expected


# info: oid end, status, device type, power type
@pytest.mark.parametrize(
    "parameters, item, info, state_expected, infotext_expected",
    [
        ((0, 0), u'1', [[u'1', u'1', u'0x35000001', u'1']], 0,
         'Supply status OK'),  # status == 1, proper ac power type
        ((0, 0), u'1', [[u'1', u'1', u'0x35000001', u'2']], 0,
         'Supply status OK'),  # status == 1, proper dc power type
        ((0, 0), u'1', [[u'1', u'1', u'0x35000001', u'0']], 3,
         'No Power supply connected to this port'),  # status == 1, power type no power supply
        ((0, 0), u'1', [[u'1', u'2', u'0x35000001', u'1']], 2,
         'Supply in error condition'),  # state != 1
        ((0, 0), u'2', [[u'1', u'1', u'0x35000001', u'1']], 3,
         'Supply not found'),  # mismatch of item and oid end
    ])
def test_check_function(check_manager, parameters, item, info, state_expected, infotext_expected):
    check = check_manager.get_check(CHECK_NAME)
    state, infotext = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext_expected in infotext
