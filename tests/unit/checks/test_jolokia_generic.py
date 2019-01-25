import pytest
from checktestlib import assertDiscoveryResultsEqual, DiscoveryResult

pytestmark = pytest.mark.checks

info = [[u'PingFederate-CUK-CDI', u'TotalRequests', u'64790', u'number'],
        [u'PingFederate-CUK-CDI', u'MaxRequestTime', u'2649', u'rate']]


@pytest.mark.parametrize("check,info,expected_result", [
    ('jolokia_generic', info, [(u'PingFederate-CUK-CDI TotalRequests', {})]),
    ('jolokia_generic.rate', info, [(u'PingFederate-CUK-CDI MaxRequestTime', {})]),
])
def test_jolokia_generic_discovery(check_manager, check, info, expected_result):
    parsed = check_manager.get_check('jolokia_generic').run_parse(info)

    check = check_manager.get_check(check)
    discovered = check.run_discovery(parsed)
    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(discovered),
        DiscoveryResult(expected_result),
    )
