import pytest

from checktestlib import (
    CheckResult,
    assertCheckResultsEqual,
)

pytestmark = pytest.mark.checks

cisco_asa_failover_info = [
    ['Failover LAN Interface', '2', 'LAN_FO GigabitEthernet0/0.777'],
    ['Primary unit (this device)', '9', 'Active unit'],
    ['Secondary unit', '10', 'Standby unit'],
]


@pytest.mark.parametrize("info,params, expected", [
    (cisco_asa_failover_info, 1, [
        (0, 'Device (primary) is the active unit'),
        (1, '(The primary device should be other)'),
    ]),
    (cisco_asa_failover_info, 9, [
        (0, 'Device (primary) is the active unit'),
    ]),
])
def test_cisco_asa_failover_params(check_manager, info, params, expected):
    check = check_manager.get_check('cisco_asa_failover')
    result = CheckResult(check.run_check(None, params, check.run_parse(info)))
    assertCheckResultsEqual(result, CheckResult(expected))
