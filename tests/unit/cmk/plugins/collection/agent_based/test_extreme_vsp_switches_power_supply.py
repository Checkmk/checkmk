#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.extreme_vsp_switches_power_supply import (
    check_vsp_switches_power_supply,
    discover_vsp_switches_power_supply,
    parse_vsp_switches_power_supply,
)

_STRING_TABLE = [
    [
        ["1", "3"],
        ["2", "4"],
    ],
    [
        ["1", "", "2", "715"],
        ["2", "800", "3", "715"],
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_discovery_result",
    [
        pytest.param(
            _STRING_TABLE,
            [
                Service(item="1"),
                Service(item="2"),
            ],
            id="For every power supply available, a Service is created.",
        ),
        pytest.param(
            [[], []],
            [],
            id="If the are no power supplies, no Services are created.",
        ),
    ],
)
def test_discover_vsp_switches_power_supply(
    string_table: list[StringTable],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_vsp_switches_power_supply(parse_vsp_switches_power_supply(string_table)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_check_result",
    [
        pytest.param(
            _STRING_TABLE,
            "1",
            [
                Result(
                    state=State.OK, summary="Operational status: up - present and supplying power"
                ),
                Result(state=State.OK, summary="Input Line Voltage high220v"),
                Result(state=State.OK, summary="Output Watts: 715"),
            ],
            id="The operational status is up, so the check state is OK.",
        ),
        pytest.param(
            _STRING_TABLE,
            "2",
            [
                Result(
                    state=State.CRIT,
                    summary="Operational status: down - present, but failure indicated",
                ),
                Result(state=State.OK, summary="Input Line Voltage minus48v"),
                Result(state=State.OK, summary="Output Watts: 715"),
                Result(state=State.OK, summary="PSE Power: 800"),
            ],
            id="The operational status is down, so the check state is CRIT.",
        ),
    ],
)
def test_check_vsp_switches_fan(
    string_table: list[StringTable],
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_vsp_switches_power_supply(
                item=item,
                section=parse_vsp_switches_power_supply(string_table),
            )
        )
        == expected_check_result
    )
