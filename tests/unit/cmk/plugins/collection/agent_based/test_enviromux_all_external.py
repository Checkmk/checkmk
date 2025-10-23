#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Callable

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
from cmk.plugins.collection.agent_based.enviromux_all_external import parse_enviromux_all_external
from cmk.plugins.lib.enviromux import (
    check_enviromux_temperature,
    discover_enviromux_humidity,
    discover_enviromux_temperature,
    discover_enviromux_voltage,
    EnviromuxSection,
)

STRING_TABLE = [
    ["0", "26", "Sensor #2.1", "0.000000 Hz", "0.000000 Hz", "200.000000 Hz"],
    ["1", "50", "Überspannungsableiter R03.A1 WM300", "0.000000", "0.000000", "0.000000"],
    ["17", "51", "Conn #2 Output Relay #1", "1.000000", "0.000000", "0.000000"],
    ["33", "32769", "Temperatur R03.A1", "27.346228 C", "something_weird", "no_value"],
    ["34", "32770", "Luftfeuchtigkeit R03.A1", "31.708282 %", "15.000000 %", "70.000000 %"],
    ["35", "24", "Taupunkt R03.A1", "9.058692 C", "0.000000 C", "50.000000 C"],
    ["36", "32769", "Temperatur R03.A2", "20.653761 C", "15.000000 C", "20.000000 C"],
    ["37", "32770", "Luftfeuchtigkeit R03.A2", "46.043915 %", "15.000000 %", "75.000000 %"],
]


@pytest.mark.parametrize(
    "discover_func, string_table, expected_discovery_result",
    [
        pytest.param(
            discover_enviromux_temperature,
            STRING_TABLE,
            [Service(item="Temperatur R03.A1 33"), Service(item="Temperatur R03.A2 36")],
            id="For every temperature sensor, a Service is discovered.",
        ),
        pytest.param(
            discover_enviromux_temperature,
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
        pytest.param(
            discover_enviromux_humidity,
            STRING_TABLE,
            [
                Service(item="Luftfeuchtigkeit R03.A1 34"),
                Service(item="Luftfeuchtigkeit R03.A2 37"),
            ],
            id="For every humidity sensor, a Service is discovered.",
        ),
        pytest.param(
            discover_enviromux_voltage,
            STRING_TABLE,
            [],
            id="No relevant voltage sensors in the input leads to no discovered Services.",
        ),
    ],
)
def test_discovery(
    discover_func: Callable[[EnviromuxSection], DiscoveryResult],
    string_table: StringTable,
    expected_discovery_result: DiscoveryResult,
) -> None:
    assert (
        list(discover_func(parse_enviromux_all_external(string_table))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_results",
    [
        pytest.param(
            STRING_TABLE,
            "Temperatur R03.A1 33",
            [
                Metric("temp", 27.346228),
                Result(state=State.OK, summary="Temperature: 27.3 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
            id="OK - No thresholds set.",
        ),
        pytest.param(
            STRING_TABLE,
            "Temperatur R03.A2 36",
            [
                Metric("temp", 20.653761, levels=(20.0, 20.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 20.7 °C (warn/crit at 20.0 °C/20.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="CRIT - Value above max threshold from device.",
        ),
    ],
)
def test_check_enviromux_all_external_temperature(
    string_table: StringTable,
    item: str,
    expected_results: CheckResult,
) -> None:
    assert (
        list(
            check_enviromux_temperature(
                item,
                None,
                parse_enviromux_all_external(string_table),
            )
        )
        == expected_results
    )
