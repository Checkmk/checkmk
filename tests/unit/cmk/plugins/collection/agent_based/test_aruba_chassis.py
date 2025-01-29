#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import aruba_chassis

DATA = [
    ["0", "Chassis", "22C", "26C", "22C", "55C", ""],
    ["1", "Chassis", "21C", "25C", "21C", "55C", ""],
    ["2", "Chassis", "56C", "70C", "30C", "55C", ""],
    ["3", "Chassis", "52C", "60C", "25C", "55C", ""],
    ["4", "Chassis", "70C", "83C", "40C", "55C", ""],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            DATA,
            [
                Service(item="Chassis 0"),
                Service(item="Chassis 1"),
                Service(item="Chassis 2"),
                Service(item="Chassis 3"),
                Service(item="Chassis 4"),
            ],
        ),
    ],
)
def test_discover_aruba_chassis_temp(
    string_table: StringTable,
    result: DiscoveryResult,
) -> None:
    section = aruba_chassis.parse_aruba_chassis(string_table)
    assert list(aruba_chassis.discover_aruba_chassis_temp(section)) == result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "Chassis 0",
            [
                Metric("temp", 22.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 22.0 °C"),
                Result(state=State.OK, notice="Configuration: show most critical state"),
                Result(state=State.OK, summary="Min temperature: 22.0 °C"),
                Result(state=State.OK, summary="Max temperature: 26.0 °C"),
            ],
        ),
        (
            DATA,
            "Chassis 1",
            [
                Metric("temp", 21.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 21.0 °C"),
                Result(state=State.OK, notice="Configuration: show most critical state"),
                Result(state=State.OK, summary="Min temperature: 21.0 °C"),
                Result(state=State.OK, summary="Max temperature: 25.0 °C"),
            ],
        ),
        (
            DATA,
            "Chassis 2",
            [
                Metric("temp", 56.0, levels=(55.0, 55.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 56.0 °C (warn/crit at 55.0 °C/55.0 °C)"
                ),
                Result(state=State.OK, notice="Configuration: show most critical state"),
                Result(state=State.OK, summary="Min temperature: 30.0 °C"),
                Result(state=State.OK, summary="Max temperature: 70.0 °C"),
            ],
        ),
        (
            DATA,
            "Chassis 3",
            [
                Metric("temp", 52.0, levels=(50.0, 60.0)),
                Result(
                    state=State.WARN, summary="Temperature: 52.0 °C (warn/crit at 50.0 °C/60.0 °C)"
                ),
                Result(state=State.OK, notice="Configuration: show most critical state"),
                Result(state=State.OK, summary="Min temperature: 25.0 °C"),
                Result(state=State.OK, summary="Max temperature: 60.0 °C"),
            ],
        ),
        (
            DATA,
            "Chassis 4",
            [
                Metric("temp", 70.0, levels=(50.0, 60.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 70.0 °C (warn/crit at 50.0 °C/60.0 °C)"
                ),
                Result(state=State.OK, notice="Configuration: show most critical state"),
                Result(state=State.OK, summary="Min temperature: 40.0 °C"),
                Result(state=State.OK, summary="Max temperature: 83.0 °C"),
            ],
        ),
    ],
)
def test_check_aruba_chassis_temp(
    string_table: StringTable,
    item: str,
    result: CheckResult,
) -> None:
    section = aruba_chassis.parse_aruba_chassis(string_table)
    assert (
        list(
            aruba_chassis.check_aruba_chassis_temp(
                item,
                aruba_chassis.default_chassis_temperature_parameters,
                section,
            )
        )
        == result
    )
