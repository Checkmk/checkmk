#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

check_name = "megaraid_bbu"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse_function(fix_register):
    return fix_register.agent_sections[SectionName(check_name)].parse_function


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, s: plugin.check_function(item=i, params={}, section=s)


@pytest.fixture(scope="function", name="section")
def _get_section(parse_megaraid_bbu):
    return parse_megaraid_bbu(
        [
            line.split()
            for line in """
BBU status for Adapter: 0

BatteryType: CVPM02
Voltage: 9437 mV
Current: 0 mA
Temperature: 27 C
BBU Firmware Status:

Charging Status : None
Voltage : OK
Temperature : OK
Learn Cycle Requested : No
Learn Cycle Active : No
Learn Cycle Status : OK
Learn Cycle Timeout : No
I2c Errors Detected : No
Battery Pack Missing : No
Battery Replacement required : No
Remaining Capacity Low : No
Periodic Learn Required : No
Transparent Learn : No
No space to cache offload : No
Pack is about to fail & should be replaced : No
Cache Offload premium feature required : No
Module microcode update required : No
BBU GasGauge Status: 0x6ef7
Pack energy : 247 J
Capacitance : 110
Remaining reserve space : 0
""".split(
                "\n"
            )
            if line
        ]
    )


def test_discovery(discover_megaraid_bbu, section) -> None:
    assert list(discover_megaraid_bbu(section)) == [Service(item="0")]


def test_check_ok(check_megaraid_bbu, section) -> None:
    assert list(check_megaraid_bbu("0", section)) == [
        Result(
            state=State.OK,
            summary="All states as expected, No charge information reported for this controller",
        )
    ]


def test_check_low_cap(check_megaraid_bbu, section) -> None:
    section["0"]["Remaining Capacity Low"] = "Yes"
    assert list(check_megaraid_bbu("0", section)) == [
        Result(
            state=State.WARN,
            summary="Remaining capacity low: Yes (expected: No), No charge information reported for this controller",
        )
    ]
