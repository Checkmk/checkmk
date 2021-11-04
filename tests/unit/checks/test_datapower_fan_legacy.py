#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

from tests.unit.conftest import FixRegister

_SECTION = [
    ["11", "9700", "4"],
    ["12", "5600", "5"],
    ["13", "9800", "7"],
    ["14", "5400", "10"],
]


@pytest.fixture(name="datapower_fan_plugin")
def fixture_datapower_fan_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("datapower_fan")]


def test_discover_datapower_fan(datapower_fan_plugin: CheckPlugin) -> None:
    assert list(datapower_fan_plugin.discovery_function(_SECTION)) == [
        Service(item="Tray 1 Fan 1"),
        Service(item="Tray 1 Fan 2"),
        Service(item="Tray 1 Fan 3"),
        Service(item="Tray 1 Fan 4"),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "Tray 1 Fan 1",
            Result(
                state=State.OK,
                summary="9700 rpm",
            ),
            id="normal",
        ),
        pytest.param(
            "Tray 1 Fan 3",
            Result(
                state=State.CRIT,
                summary="reached upper non-recoverable limit: 9800 rpm",
            ),
            id="upper critical limit",
        ),
    ],
)
def test_check_datapower_fan(
    datapower_fan_plugin: CheckPlugin,
    item: str,
    expected_result: Result,
) -> None:
    assert (
        list(
            datapower_fan_plugin.check_function(
                item=item,
                params={},
                section=_SECTION,
            )
        )
        == [expected_result]
    )
