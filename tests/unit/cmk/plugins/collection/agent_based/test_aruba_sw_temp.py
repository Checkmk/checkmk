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
from cmk.plugins.collection.agent_based import aruba_sw_temp

DATA = [
    ["1.3.1.1", "1/1-PHY-01-08", "emergency", "81000", "49000", "86000"],
    ["1.3.1.2", "1/1-PHY-09-16", "normal", "92000", "50000", "87000"],
    ["1.3.1.3", "1/1-PHY-17-24", "normal", "83000", "50000", "88000"],
    ["1.3.1.4", "1/1-Inlet-Air", "normal", "37875", "19750", "43250"],
    ["1.3.1.5", "1/1-Switch-ASIC-Internal", "normal", "62000", "46375", "66875"],
    ["1.3.1.6", "1/1-Switch-CPU-1", "normal", "61625", "46000", "66500"],
    ["1.3.1.7", "1/1-Switch-CPU-2", "fault", "63125", "47000", "68250"],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            DATA,
            [
                Service(item="1/1-PHY-01-08"),
                Service(item="1/1-PHY-09-16"),
                Service(item="1/1-PHY-17-24"),
                Service(item="1/1-Inlet-Air"),
                Service(item="1/1-Switch-ASIC-Internal"),
                Service(item="1/1-Switch-CPU-1"),
                Service(item="1/1-Switch-CPU-2"),
            ],
        ),
    ],
)
def test_discover_aruba_sw_temp_status(
    string_table: StringTable,
    result: DiscoveryResult,
) -> None:
    section = aruba_sw_temp.parse_aruba_sw_temp(string_table)
    assert list(aruba_sw_temp.discover_aruba_sw_temp(section)) == result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "1/1-PHY-01-08",
            [
                Metric("temp", 81.0, levels=(81.7, 86.0)),
                Result(state=State.OK, summary="Temperature: 81.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.CRIT, summary="Device status: emergency"),
            ],
        ),
        (
            DATA,
            "1/1-PHY-09-16",
            [
                Metric("temp", 92.0, levels=(82.64999999999999, 87.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 92.0 °C (warn/crit at 82.6 °C/87.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
            ],
        ),
        (
            DATA,
            "1/1-PHY-17-24",
            [
                Metric("temp", 83.0, levels=(83.6, 88.0)),
                Result(state=State.OK, summary="Temperature: 83.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
            ],
        ),
        (
            DATA,
            "1/1-Inlet-Air",
            [
                Metric("temp", 37.875, levels=(41.0875, 43.25)),
                Result(state=State.OK, summary="Temperature: 37.9 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-ASIC-Internal",
            [
                Metric("temp", 62.0, levels=(63.53125, 66.875)),
                Result(state=State.OK, summary="Temperature: 62.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-CPU-1",
            [
                Metric("temp", 61.625, levels=(63.175, 66.5)),
                Result(state=State.OK, summary="Temperature: 61.6 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
                Result(state=State.OK, summary="Device status: normal"),
            ],
        ),
        (
            DATA,
            "1/1-Switch-CPU-2",
            [
                Result(state=State.WARN, summary="Device status: fault"),
            ],
        ),
    ],
)
def test_check_aruba_fan_status(
    string_table: StringTable,
    item: str,
    result: CheckResult,
) -> None:
    section = aruba_sw_temp.parse_aruba_sw_temp(string_table)
    assert (
        list(
            aruba_sw_temp.check_aruba_sw_temp(
                item,
                aruba_sw_temp.aruba_sw_temp_check_default_parameters,
                section,
            )
        )
        == result
    )
