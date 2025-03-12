#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.collection.agent_based.datapower_temp import (
    check_datapower_temp,
    discover_datapower_temp,
    parse_datapower_temp,
)

_STRING_TABLE = [
    ["Temperature CPU1", "50.0", "65.0", "1", "70.0"],
    ["Temperature CPU2", "40.0", "35.0", "1", "50.0"],
    ["Temperature CPU3", "70.0", "", "1", "60.0"],
    ["Temperature CPU4", "20.0", "65.0", "9", "70.0"],
    ["Temperature CPU5", "20.0", "65.0", "8", "70.0"],
]


def test_discover_datapower_temp() -> None:
    assert list(discover_datapower_temp(parse_datapower_temp(_STRING_TABLE))) == [
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
                Metric("temp", 50.0, levels=(65.0, 70.0)),
                Result(state=State.OK, summary="Temperature: 50.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="normal",
        ),
        pytest.param(
            "CPU2",
            [
                Metric("temp", 40.0, levels=(35.0, 50.0)),
                Result(
                    state=State.WARN, summary="Temperature: 40.0 °C (warn/crit at 35.0 °C/50.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="WARN",
        ),
        pytest.param(
            "CPU3",
            [
                Metric("temp", 70.0),
                Result(state=State.OK, summary="Temperature: 70.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
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
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_datapower_temp(
                item=item,
                params={},
                section=parse_datapower_temp(_STRING_TABLE),
            )
        )
        == expected_result
    )
