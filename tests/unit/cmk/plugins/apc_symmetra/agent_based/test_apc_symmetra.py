#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.apc_symmetra.agent_based import apc_symmetra

STRING_TABLE_1 = [
    [],
    [
        [
            "1",
            "2",
            "2",
            "100",
            "2",
            "0",
            "366000",
            "2",
            "06/20/2012",
            "18",
            "0",
            "0001010000000000001000000000000000000000000000000000000000000000",
        ]
    ],
]
STRING_TABLE_2 = [
    [],
    [
        [
            "1",
            "2",
            "2",
            "100",
            "1",
            "0",
            "366000",
            "2",
            "06/20/2012",
            "18",
            "0",
            "0001010000000000001000000000000000000000000000000000000000000000",
        ]
    ],
]
STRING_TABLE_3 = [
    [],
    [
        [
            "1",
            "2",
            "2",
            "99",
            "1",
            "",
            "5182500",
            "2",
            "05/23/2025",
            "21",
            "",
            "0001010000000000001000000000000000000000000000000000000000000000",
        ]
    ],
    [
        ["0010000000000000"],
        ["0000000000000000"],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
        [""],
    ],
]


@pytest.mark.parametrize(
    ["string_table", "params", "expected"],
    [
        pytest.param(
            STRING_TABLE_1,
            {"capacity": ("fixed", (95, 80)), "calibration_state": 0, "battery_replace_state": 1},
            [
                Result(state=State.OK, summary="Battery status: normal"),
                Result(state=State.WARN, summary="Battery needs replacing"),
                Result(state=State.OK, summary="Output status: on line (calibration invalid)"),
                Result(state=State.OK, summary="Capacity: 100.00%"),
                Metric(name="capacity", value=100.0, boundaries=(0, 100)),
                Result(state=State.OK, summary="Time remaining: 1 hour 1 minute"),
                Metric(name="runtime", value=3660.0),
            ],
        ),
        pytest.param(
            STRING_TABLE_1,
            {"capacity": ("fixed", (95, 80)), "calibration_state": 0, "battery_replace_state": 2},
            [
                Result(state=State.OK, summary="Battery status: normal"),
                Result(state=State.CRIT, summary="Battery needs replacing"),
                Result(state=State.OK, summary="Output status: on line (calibration invalid)"),
                Result(state=State.OK, summary="Capacity: 100.00%"),
                Metric(name="capacity", value=100.0, boundaries=(0, 100)),
                Result(state=State.OK, summary="Time remaining: 1 hour 1 minute"),
                Metric(name="runtime", value=3660.0),
            ],
        ),
        pytest.param(
            STRING_TABLE_2,
            {"capacity": ("fixed", (95, 80)), "calibration_state": 0, "battery_replace_state": 0},
            [
                Result(state=State.OK, summary="Battery status: normal"),
                Result(state=State.OK, summary="No battery needs replacing"),
                Result(state=State.OK, summary="Output status: on line (calibration invalid)"),
                Result(state=State.OK, summary="Capacity: 100.00%"),
                Metric("capacity", value=100.0, boundaries=(0, 100)),
                Result(state=State.OK, summary="Time remaining: 1 hour 1 minute"),
                Metric(name="runtime", value=3660.0),
            ],
        ),
        pytest.param(
            STRING_TABLE_3,
            {"capacity": ("fixed", (95, 80)), "calibration_state": 0, "battery_replace_state": 0},
            [
                Result(state=State.OK, summary="Battery status: normal"),
                Result(state=State.OK, summary="No battery needs replacing"),
                Result(state=State.OK, summary="Output status: on line (calibration invalid)"),
                Result(state=State.OK, summary="Capacity: 99.00%"),
                Metric(name="capacity", value=99.0, boundaries=(0, 100)),
                Result(state=State.OK, summary="Time remaining: 14 hours 23 minutes"),
                Metric(name="runtime", value=51825.0),
                Result(state=State.WARN, summary="Battery pack cartridge 0: Needs Replacement"),
                Result(state=State.OK, summary="Battery pack cartridge 1: OK"),
            ],
        ),
    ],
)
def test_check(
    string_table: apc_symmetra.ExtendedStringTable,
    params: Mapping[str, object],
    expected: CheckResult,
) -> None:
    assert (
        list(apc_symmetra.check_apc_symmetra(params, apc_symmetra.parse_apc_symmetra(string_table)))
        == expected
    )


@pytest.mark.parametrize(
    ["string_table", "item", "params", "expected"],
    [
        pytest.param(
            STRING_TABLE_1,
            "Battery",
            {"current": (1, 1)},
            [
                Result(state=State.OK, summary="Current: 0.0 A"),
                Metric(name="current", value=0.0, levels=(1, 1)),
            ],
        )
    ],
)
def test_check_elphase(
    string_table: apc_symmetra.ExtendedStringTable,
    item: str,
    params: Mapping[str, object],
    expected: CheckResult,
) -> None:
    assert (
        list(
            apc_symmetra.check_apc_symmetra_elphase(
                item, params, apc_symmetra.parse_apc_symmetra(string_table)
            )
        )
        == expected
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["string_table", "item", "params", "expected"],
    [
        pytest.param(
            STRING_TABLE_1,
            "Battery",
            {"levels": (50, 60)},
            [
                Metric(name="temp", value=18.0, levels=(50.0, 60.0)),
                Result(state=State.OK, summary="Temperature: 18.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
        )
    ],
)
def test_check_temp(
    string_table: apc_symmetra.ExtendedStringTable,
    item: str,
    params: Mapping[str, object],
    expected: CheckResult,
) -> None:
    assert (
        list(
            apc_symmetra.check_apc_symmetra_temp(
                item, params, apc_symmetra.parse_apc_symmetra(string_table)
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    ["string_table", "discovery_func", "expected"],
    [
        pytest.param(STRING_TABLE_1, apc_symmetra.discovery_apc_symmetra, [Service()]),
        pytest.param(
            STRING_TABLE_1, apc_symmetra.discovery_apc_symmetra_elphase, [Service(item="Battery")]
        ),
        pytest.param(
            STRING_TABLE_1, apc_symmetra.discovery_apc_symmetra_temp, [Service(item="Battery")]
        ),
        pytest.param(STRING_TABLE_3, apc_symmetra.discovery_apc_symmetra, [Service()]),
        pytest.param(STRING_TABLE_3, apc_symmetra.discovery_apc_symmetra_elphase, []),
        pytest.param(
            STRING_TABLE_3, apc_symmetra.discovery_apc_symmetra_temp, [Service(item="Battery")]
        ),
    ],
)
def test_discovery(
    string_table: apc_symmetra.ExtendedStringTable,
    discovery_func: Callable[[Mapping[str, Any]], DiscoveryResult],
    expected: list[Service],
) -> None:
    assert list(discovery_func(apc_symmetra.parse_apc_symmetra(string_table))) == expected
