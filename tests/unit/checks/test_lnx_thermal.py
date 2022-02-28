#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]

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
result_discovery = [  # type: ignore
    [('Zone %s' % i, {}) for i in [0, 1, 3, 5]],
    [('Zone %s' % i, {}) for i in [0, 3, 4, 5, 6]],
]


@pytest.mark.parametrize("info, result", list(zip(agent_info, result_discovery)))
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse_and_discovery_function(info, result):
    check = Check("lnx_thermal")
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


@pytest.mark.parametrize("info, discovered, checked",
                         list(zip(agent_info, result_discovery, result_check)))
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_functions_perfdata(info, discovered, checked):
    check = Check("lnx_thermal")
    parsed = check.run_parse(info)
    for (item, _params), result in zip(discovered, checked):
        assert check.run_check(item, {}, parsed) == result


@pytest.mark.parametrize(
    "line, item",
    [
        (
            [
                "thermal_zone0",
                "enabled",
                "acpitz",
                "27800",
                "105000",
                "critical",
                "80000",
                "active",
                "55000",
                "active",
                "500",
                "00",
                "active",
                "45000",
                "active",
                "40000",
                "active",
            ],
            "Zone 0",
        ),
        (
            [
                "thermal_zone1",
                "enabled",
                "acpitz",
                "29800",
                "105000",
                "critical",
                "108000",
                "passive",
            ],
            "Zone 1",
        ),
    ],
)
def test_parse_and_discovery_function_2(line, item):
    check = Check("lnx_thermal")
    parsed = check.run_parse([line])
    assert DiscoveryResult(check.run_discovery(parsed)) == DiscoveryResult([(item, {})])


@pytest.mark.parametrize(
    "line, item, result",
    [
        (
            [
                "thermal_zone0",
                "enabled",
                "acpitz",
                "27800",
                "105000",
                "critical",
                "80000",
                "active",
                "55000",
                "active",
                "500",
                "00",
                "active",
                "45000",
                "active",
                "40000",
                "active",
            ],
            "Zone 0",
            (0, "27.8 \xb0C", [("temp", 27.8, None, None)]),
        ),
        (
            [
                "thermal_zone1",
                "enabled",
                "acpitz",
                "29800",
                "105000",
                "critical",
                "108000",
                "passive",
            ],
            "Zone 1",
            (0, "29.8 \xb0C", [("temp", 29.8, 108.0, 105.0)]),
        ),
    ],
)
def test_check_functions_perfdata_2(line, item, result):
    check = Check("lnx_thermal")
    parsed = check.run_parse([line])
    assert check.run_check(item, {}, parsed) == result
