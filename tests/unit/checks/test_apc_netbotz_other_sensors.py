#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.checkengine.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

TEST_INFO: Sequence[Sequence[str]] = [
    ["Ethernet Link Status", "0", "Up"],
    ["A-Link Bus Power", "0", "OK"],
    ["Sensor A", "1", "Error"],
]


@pytest.mark.parametrize(
    "expected_result",
    [
        ([Service()]),
    ],
)
def test_inventory_apc_netbotz_other_sensors(
    fix_register: FixRegister,
    expected_result: Sequence[Result | Metric],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("apc_netbotz_other_sensors")]
    result = list(check_plugin.discovery_function(TEST_INFO))
    assert result == expected_result


def test_check_apc_netbotz_other_sensors(
    fix_register: FixRegister,
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("apc_netbotz_other_sensors")]
    result = list(check_plugin.check_function(params={}, section=TEST_INFO))
    assert result == [
        Result(state=State.CRIT, summary="Sensor A: error"),
        Result(state=State.OK, summary="2 sensors are OK"),
    ]
