#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.apc_netbotz_sensors import (
    check_apc_netbotz_sensors_dewpoint,
    check_apc_netbotz_sensors_humidity,
    check_apc_netbotz_sensors_temp,
    parse_apc_netbotz_v2_sensors,
)
from cmk.plugins.lib.temperature import TempParamType

TEST_INFO: list[StringTable] = [
    [
        ["nbAlinkEnc_0_4_TEMP", "252", "Temp 03.01.190-19 (4)", "25.200000"],
        ["nbAlinkEnc_0_5_TEMP", "0", "Temperature  (5)", ""],
    ],
    [
        ["nbAlinkEnc_1_5_HUMI", "370", "Hum 03.01.190-25 (5)", "37.000000"],
        ["nbAlinkEnc_0_6_HUMI", "0", "Humidity  (6)", ""],
    ],
    [
        ["nbAlinkEnc_0_5_DWPT", "0", "Dew Point  (5)", ""],
        ["nbAlinkEnc_0_3_DWPT", "61", "Dew Point  (3)", "6.100000"],
    ],
]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_0_4_TEMP",
            {"output_unit": "k", "levels": (18.0, 25.0), "levels_lower": (-4.0, -6.0)},
            [
                Result(state=State.OK, summary="[Temp 03.01.190-19 (4)]"),
                Metric("temp", 25.2, levels=(18.0, 25.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 298.3 K (warn/crit at 291.1 K/298.1 K)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="temp reading",
        ),
        pytest.param("nbAlinkEnc_0_5_TEMP", {}, [], id="temp reading not present"),
        pytest.param("nbAlinkEnc_0_3_DWPT", {}, [], id="dew reading"),
    ],
)
def test_apc_netbotz_sensors_temp(
    item: str,
    params: TempParamType,
    expected_result: Sequence[Result | Metric],
) -> None:
    parsed = parse_apc_netbotz_v2_sensors(TEST_INFO)
    result = list(check_apc_netbotz_sensors_temp(item=item, params=params, section=parsed))
    assert result == expected_result


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_1_5_HUMI",
            {"levels": (1.0, 2.0), "levels_lower": (3.0, 4.0)},
            [
                Result(state=State.OK, summary="[Hum 03.01.190-25 (5)]"),
                Result(
                    state=State.CRIT,
                    summary="37.00% (warn/crit at 1.00%/2.00%)",
                ),
                Metric("humidity", 37.0, levels=(1.0, 2.0), boundaries=(0.0, 100.0)),
            ],
            id="humidity reading",
        ),
        pytest.param("nbAlinkEnc_0_6_HUMI", {}, [], id="humidity reading not present"),
    ],
)
def test_apc_netbotz_sensors_humidity(
    item: str,
    params: Mapping[str, object],
    expected_result: Sequence[Result | Metric],
) -> None:
    parsed = parse_apc_netbotz_v2_sensors(TEST_INFO)
    result = list(check_apc_netbotz_sensors_humidity(item=item, params=params, section=parsed))
    assert result == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "nbAlinkEnc_0_3_DWPT",
            [
                Result(state=State.OK, summary="[Dew Point  (3)]"),
                Metric("temp", 6.1),
                Result(state=State.OK, summary="Temperature: 6.1 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
            id="dewpoint reading",
        ),
        pytest.param("nbAlinkEnc_0_5_DWPT", [], id="dewpoint reading not present"),
    ],
)
def test_apc_netbotz_sensors_dewpoint(
    item: str,
    expected_result: Sequence[Result | Metric],
) -> None:
    parsed = parse_apc_netbotz_v2_sensors(TEST_INFO)
    result = list(check_apc_netbotz_sensors_dewpoint(item=item, params={}, section=parsed))
    assert result == expected_result
