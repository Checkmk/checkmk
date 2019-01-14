# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks

def splitter(text, split_symbol=None):
    return [line.split(split_symbol) for line in text.split("\n")]

agent_info = [
    splitter("""thermal_zone0 enabled acpitz 57000 127000 critical
thermal_zone1 enabled acpitz 65000 100000 critical 95500 passive
thermal_zone3 - pch_skylake 46000 115000 critical
thermal_zone5 pkg-temp-0  44000 0 passive 0 passive"""),
    splitter(
        """thermal_zone0|enabled|acpitz|25000|107000|critical
thermal_zone3|-|pch_skylake|45000|115000|critical
thermal_zone4|-|INT3400 Thermal|20000
thermal_zone5|-|x86_pkg_temp|48000|0|passive|0|passive
thermal_zone6|-|B0D4|61000|127000|critical|127000|hot|99000|passive|99000|active|94000|active""",
        '|')
]
result_discovery = [[('Zone %s' % i, {}) for i in [0, 1, 3, 5]],
                    [('Zone %s' % i, {}) for i in [0, 3, 4, 5, 6]]]


@pytest.mark.parametrize("info, result", zip(agent_info, result_discovery))
def test_parse_and_discovery_function(check_manager, info, result):
    check = check_manager.get_check("lnx_thermal")
    parsed = check.run_parse(info)
    discovery = DiscoveryResult(check.run_discovery(parsed))
    assertDiscoveryResultsEqual(check, discovery, DiscoveryResult(result))


result_check = [
    [
        (0, '57.0 °C', [('temp', 57.0, 127.0, 127.0)]),
        (0, '65.0 °C', [('temp', 65.0, 95.5, 100.0)]),
        (0, '46.0 °C', [('temp', 46.0, 115.0, 115.0)]),
        (0, '44.0 °C', [('temp', 44.0, None, None)]),
    ],
    [
        (0, '25.0 °C', [('temp', 25.0, 107.0, 107.0)]),
        (0, '45.0 °C', [('temp', 45.0, 115.0, 115.0)]),
        (0, '20.0 °C', [('temp', 20.0, None, None)]),
        (0, '48.0 °C', [('temp', 48.0, None, None)]),
        (0, '61.0 °C', [('temp', 61.0, 99.0, 127.0)]),
    ],
]

@pytest.mark.parametrize("info, discovered, checked", zip(agent_info, result_discovery,
                                                          result_check))
def test_check_functions_perfdata(check_manager, info, discovered, checked):
    check = check_manager.get_check("lnx_thermal")
    parsed = check.run_parse(info)
    for (item, params), result in zip(discovered, checked):
        assert check.run_check(item, {}, parsed) == result
