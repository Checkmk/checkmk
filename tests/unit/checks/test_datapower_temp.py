#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_STRING_TABLE = [
    ["Temperature CPU1", "50.0", "65.0", "1", "70.0"],
    ["Temperature CPU2", "40.0", "35.0", "1", "50.0"],
    ["Temperature CPU3", "70.0", "", "1", "60.0"],
    ["Temperature CPU4", "20.0", "65.0", "9", "70.0"],
    ["Temperature CPU5", "20.0", "65.0", "8", "70.0"],
]


@pytest.fixture(name="datapower_temp_plugin")
def fixture_datapower_temp_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("datapower_temp")]


def test_discover_datapower_temp(datapower_temp_plugin: CheckPlugin) -> None:
    assert list(datapower_temp_plugin.discovery_function(_STRING_TABLE)) == [
        Service(item="CPU1"),
        Service(item="CPU2"),
        Service(item="CPU3"),
        Service(item="CPU4"),
        Service(item="CPU5"),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "CPU1",
            [
                Result(state=State.OK, summary="50.0 °C"),
                Metric("temp", 50.0, levels=(65.0, 70.0)),
            ],
            id="normal",
        ),
        pytest.param(
            "CPU2",
            [
                Result(state=State.WARN, summary="40.0 °C (device warn/crit at 35.0/50.0 °C)"),
                Metric("temp", 40.0, levels=(35.0, 50.0)),
            ],
            id="WARN",
        ),
        pytest.param(
            "CPU3",
            [
                Result(state=State.OK, summary="70.0 °C"),
                Metric("temp", 70.0),
            ],
            id="missing dev_warn_level",
        ),
        pytest.param(
            "CPU4",
            [Result(state=State.UNKNOWN, summary="device status: noReading")],
            id="no reading",
        ),
        pytest.param(
            "CPU5",
            [Result(state=State.CRIT, summary="device status: failure")],
            id="failure",
        ),
    ],
)
def test_check_datapower_temp(
    datapower_temp_plugin: CheckPlugin,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            datapower_temp_plugin.check_function(
                item=item,
                params={},
                section=_STRING_TABLE,
            )
        )
        == expected_result
    )
