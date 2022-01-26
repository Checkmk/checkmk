#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.api.agent_based.register as agent_based_register

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_STRING_TABLE = [
    ["DIMM A1 temperature", "30", "1", "0", "5"],
    ["DIMM A2 temperature", "30", "1", "0", "5"],
    ["PCH temperature", "45", "1", "0", "5"],
    ["SAS controller temperature", "37", "1", "0", "5"],
    ["SSL card temperature", "26", "4", "0", "5"],
    ["System center temperature", "37", "1", "0", "5"],
    ["System left temperature", "30", "1", "0", "5"],
    ["System right temperature", "33", "1", "0", "5"],
    ["CPU temperature", "39", "1", "0", "5"],
    ["System fan 1 front speed", "8100", "1", "0", "6"],
    ["System fan 1 rear speed", "6800", "1", "0", "6"],
    ["+3.3V main bus voltage", "3244", "1", "-3", "4"],
    ["+3.3V standby voltage", "3199", "1", "-3", "4"],
    ["+5V main bus voltage", "50508", "1", "-4", "4"],
    ["+5V standby voltage", "50508", "1", "-4", "4"],
    ["BMC PLL voltage", "1264", "1", "-3", "4"],
    ["CPU core voltage", "8428", "1", "-4", "4"],
    ["CPU PLL voltage", "18326", "1", "-4", "4"],
    ["CPU system agent voltage", "9310", "1", "-4", "4"],
    ["CPU termination voltage", "1064", "1", "-3", "4"],
    ["Memory I/O voltage", "1520", "1", "-3", "4"],
    ["Memory termination voltage", "752", "1", "-3", "4"],
    ["PCH core voltage", "1112", "1", "-3", "4"],
    ["PCH SAS voltage", "1520", "1", "-3", "4"],
    ["SAS core voltage", "1040", "1", "-3", "4"],
    ["SAS I/O voltage", "18326", "1", "-4", "4"],
    ["SSL core voltage", "904", "4", "-3", "4"],
    ["SSL PLL voltage", "1800", "4", "-3", "4"],
    ["SSL VPTX voltage", "1800", "4", "-3", "4"],
    ["Power supply 1 status", "8", "1", "0", "3"],
    ["Power supply 2 status", "8", "1", "0", "3"],
]


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_bluecoat_sensors() -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("bluecoat_sensors"))
    assert plugin
    assert list(plugin.discovery_function(_STRING_TABLE)) == [
        Service(item="System fan 1 front speed"),
        Service(item="System fan 1 rear speed"),
        Service(item="+3.3V main bus voltage"),
        Service(item="+3.3V standby voltage"),
        Service(item="+5V main bus voltage"),
        Service(item="+5V standby voltage"),
        Service(item="BMC PLL voltage"),
        Service(item="CPU core voltage"),
        Service(item="CPU PLL voltage"),
        Service(item="CPU system agent voltage"),
        Service(item="CPU termination voltage"),
        Service(item="Memory I/O voltage"),
        Service(item="Memory termination voltage"),
        Service(item="PCH core voltage"),
        Service(item="PCH SAS voltage"),
        Service(item="SAS core voltage"),
        Service(item="SAS I/O voltage"),
        Service(item="SSL core voltage"),
        Service(item="SSL PLL voltage"),
        Service(item="SSL VPTX voltage"),
        Service(item="Power supply 1 status"),
        Service(item="Power supply 2 status"),
    ]


@pytest.mark.parametrize(
    [
        "item",
        "expected_result",
    ],
    [
        pytest.param(
            "+3.3V main bus voltage",
            [
                Result(state=State.OK, summary="3.2 V"),
                Metric("voltage", 3.244),
            ],
            id="voltage ok",
        ),
        pytest.param(
            "SSL VPTX voltage",
            [
                Result(state=State.CRIT, summary="1.8 V"),
                Metric("voltage", 1.8),
            ],
            id="voltage crit",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_bluecoat_sensors(
    item: str,
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("bluecoat_sensors"))
    assert plugin
    assert (list(plugin.check_function(
        item=item,
        params={},
        section=_STRING_TABLE,
    )) == expected_result)


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_bluecoat_sensors_temp() -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("bluecoat_sensors_temp"))
    assert plugin
    assert list(plugin.discovery_function(_STRING_TABLE)) == [
        Service(item="DIMM A1"),
        Service(item="DIMM A2"),
        Service(item="PCH"),
        Service(item="SAS controller"),
        Service(item="SSL card"),
        Service(item="System center"),
        Service(item="System left"),
        Service(item="System right"),
        Service(item="CPU"),
    ]


@pytest.mark.parametrize(
    [
        "item",
        "expected_result",
    ],
    [
        pytest.param(
            "System center",
            [
                Result(state=State.OK, summary="37.0 °C"),
                Metric("temp", 37.0),
            ],
            id="ok",
        ),
        pytest.param(
            "SSL card",
            [
                Result(state=State.OK, summary="26.0 °C"),
                Metric("temp", 26.0),
            ],
            id="crit",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_bluecoat_sensors_temp(
    item: str,
    expected_result: CheckResult,
) -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("bluecoat_sensors_temp"))
    assert plugin
    assert (list(plugin.check_function(
        item=item,
        params={},
        section=_STRING_TABLE,
    )) == expected_result)
