import pytest
from checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks

RA32E_SWITCH = 'ra32e_switch'


@pytest.mark.parametrize('info,result', [([[
    '1',
    '1',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
    '0',
]], [('Sensor 01', None), ('Sensor 02', None), ('Sensor 03', None), ('Sensor 04', None),
     ('Sensor 05', None), ('Sensor 06', None), ('Sensor 07', None), ('Sensor 08', None),
     ('Sensor 09', None), ('Sensor 10', None), ('Sensor 11', None), ('Sensor 12', None),
     ('Sensor 13', None), ('Sensor 14', None), ('Sensor 15', None), ('Sensor 16', None)])])
def test_ra32e_switch_discovery(check_manager, info, result):
    check = check_manager.get_check(RA32E_SWITCH)
    assert list(check.run_discovery(info)) == result


def test_ra32e_switch_check_closed_no_rule(check_manager):
    check = check_manager.get_check(RA32E_SWITCH)
    result = BasicCheckResult(*check.run_check("Sensor 01", None, [['1']]))

    assert result.status == 0
    assert result.infotext.startswith("closed")


def test_ra32e_switch_check_open_expected_close(check_manager):
    check = check_manager.get_check(RA32E_SWITCH)
    result = BasicCheckResult(*check.run_check(
        "Sensor 03", 'closed',
        [['1', '1', '0', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1']]))

    assert result.status == 2
    assert result.infotext.startswith("open")
    assert "expected closed" in result.infotext


def test_ra32e_switch_check_no_input(check_manager):
    check = check_manager.get_check(RA32E_SWITCH)
    result = BasicCheckResult(*check.run_check("Sensor 01", 'ignore', [['']]))

    assert result.status == 3
