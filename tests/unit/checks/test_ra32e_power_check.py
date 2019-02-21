import pytest
from checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks

RA32E_POWER = "ra32e_power"


@pytest.mark.parametrize("info,result", [([[u'']], None), ([[u'0']], [(None, {})])])
def test_ra32e_power_discovery(check_manager, info, result):
    check = check_manager.get_check(RA32E_POWER)
    assert check.run_discovery(info) == result


def test_ra32e_power_check_battery(check_manager):
    check = check_manager.get_check(RA32E_POWER)
    result = check.run_check(None, {}, [['0']])

    assert len(result) == 2
    status, infotext = result
    assert status == 1
    assert "battery" in infotext


def test_ra32e_power_check_acpower(check_manager):
    check = check_manager.get_check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [['1']]))

    assert result.status == 0
    assert 'AC/Utility' in result.infotext


def test_ra32e_power_check_nodata(check_manager):
    check = check_manager.get_check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [['']]))

    assert result.status == 3
    assert 'unknown' in result.infotext
