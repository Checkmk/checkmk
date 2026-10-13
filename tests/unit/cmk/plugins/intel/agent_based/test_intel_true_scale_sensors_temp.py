#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.intel.agent_based.intel_true_scale_sensors_temp import (
    _check_intel_true_scale_sensors_temp,
    discover_intel_true_scale_sensors_temp,
    parse_intel_true_scale_sensors,
)
from cmk.plugins.lib.temperature import TempParamDict

# synthetic data
STRING_TABLE: Sequence[StringTable] = [
    [["1", "2"], ["2", "9"], ["3", "0"], ["4", "20"], ["5", "5"]],
    [
        ["1.1.1", "2", "4", "FUSION -- baseboard temp", "41"],
        ["1.1.2", "2", "3", "FUSION -- fusion temp", "32"],
        ["1.1.3", "2", "1", "FUSION -- inlet air temp", "35"],
        ["1.1.4", "2", "5", " FUSION -- baseboard temp", "36"],
        ["1.2.1", "2", "2", "FUSION -- baseboard temp", "49"],
        ["1.2.2", "2", "0", "FUSION -- fusion temp", "31"],
        ["1.3.1", "3", "4", "FUSION -- fan1 speed", "3000"],
        ["9.4.7", "2", "3", "FUSION -- outlet air temp", "40"],
        ["1.4.1", "5", "1", "FUSION -- psu1 voltage", "12000"],
    ],
]


def test_discover_intel_true_scale_sensors_temp_needs_a_temperature_sensor() -> None:
    assert list(
        discover_intel_true_scale_sensors_temp(parse_intel_true_scale_sensors(STRING_TABLE))
    ) == [Service(item="slot 1"), Service(item="slot 2"), Service(item="slot 4")]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        pytest.param(
            "slot 1",
            [
                Result(state=State.OK, summary="Sensors: 4"),
                Result(state=State.OK, summary="Highest: 41.0 °C"),
                Metric("temp", 41.0),
                Result(state=State.OK, summary="Average: 36.0 °C"),
                Result(state=State.OK, summary="Lowest: 32.0 °C"),
                Result(
                    state=State.WARN,
                    summary="2 fusion: Temperature: 32.0 °C, State on device: warning",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="3 inlet air: Temperature: 35.0 °C, State on device: unknown",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="4 -- baseboard: Temperature: 36.0 °C, State on device: disabled",
                ),
            ],
            id="good_sensor_stays_silent_and_names_keep_their_sensor_index",
        ),
        pytest.param(
            "slot 2",
            [
                Result(state=State.OK, summary="Sensors: 2"),
                Result(state=State.OK, summary="Highest: 49.0 °C"),
                Metric("temp", 49.0),
                Result(state=State.OK, summary="Average: 40.0 °C"),
                Result(state=State.OK, summary="Lowest: 31.0 °C"),
                Result(
                    state=State.CRIT,
                    summary="1 baseboard: Temperature: 49.0 °C, State on device: bad",
                ),
                Result(
                    state=State.CRIT,
                    summary="2 fusion: Temperature: 31.0 °C, State on device: invalid",
                ),
            ],
            id="bad_and_invalid_are_both_crit",
        ),
        pytest.param(
            "slot 4",
            [
                Result(state=State.OK, summary="Sensors: 1"),
                Result(state=State.OK, summary="Highest: 40.0 °C"),
                Metric("temp", 40.0),
                Result(state=State.OK, summary="Average: 40.0 °C"),
                Result(state=State.OK, summary="Lowest: 40.0 °C"),
                Result(
                    state=State.WARN,
                    summary="7 outlet air: Temperature: 40.0 °C, State on device: warning",
                ),
            ],
            id="voltage_sensor_is_left_out_and_only_the_last_two_oid_components_count",
        ),
        pytest.param("slot 9", [], id="unknown_item"),
    ],
)
def test_check_intel_true_scale_sensors_temp(item: str, expected_results: Sequence[object]) -> None:
    assert (
        list(
            _check_intel_true_scale_sensors_temp(
                item, TempParamDict(), parse_intel_true_scale_sensors(STRING_TABLE), {}
            )
        )
        == expected_results
    )
