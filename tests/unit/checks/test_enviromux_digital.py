#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.check_legacy_includes.enviromux import parse_enviromux_digital
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [
    ["0", "Digital Input #1", "1", "1"],
    ["1", "Digital Input #2", "1", "1"],
    ["2", "Digital Input #3", "1", "1"],
]


@pytest.fixture(name="check")
def _enviromux_digital_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("enviromux_digital")]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="Digital Input #1 0"),
                Service(item="Digital Input #2 1"),
                Service(item="Digital Input #3 2"),
            ],
            id="For every digital sensor, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_enviromux_digital(
    check: CheckPlugin,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(check.discovery_function(parse_enviromux_digital(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Result(state=State.OK, summary="Sensor Value is normal: open")],
            id="If the sensor value is equal to the normal/expected value, the check result is OK.",
        ),
        pytest.param(
            [["0", "Digital Input #1", "0", "1"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Sensor Value is not normal: closed . It should be: open",
                )
            ],
            id="If the sensor value is not equal to the normal/expected value, the check result is CRIT.",
        ),
    ],
)
def test_check_enviromux_digital(
    check: CheckPlugin,
    section: StringTable,
    expected_discovery_result: Sequence[Result],
) -> None:
    assert (
        list(
            check.check_function(
                item="Digital Input #1 0",
                params={},
                section=parse_enviromux_digital(section),
            )
        )
        == expected_discovery_result
    )
