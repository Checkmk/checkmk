#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResults,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import akcp_sensor

STRING_TABLE_1 = [["Dual Humidity Port 1", "30", "7", "1"]]
STRING_TABLE_2 = [["Humidity1 Description", "", "7", "1"], ["Humidity2 Description", "", "0", "2"]]

# Rows as reported by the device of SUP-29863, which intermittently drops fields.
TEMP_TABLE_CORRUPTED = [
    ["Temperature 1", "34", "C", "2", "100", "150", "", "", "344", "1"],
    ["", "", "", "0", "", "", "", "", "", ""],
]
RELAY_TABLE_CORRUPTED = [["Water Sensor 1", "", ""], ["", "2", "1"]]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            STRING_TABLE_1,
            [Service(item="Dual Humidity Port 1")],
        ),
        (
            STRING_TABLE_2,
            [Service(item="Humidity1 Description")],
        ),
    ],
)
def test_akcp_humidity_discover(
    string_table: StringTable, expected_result: DiscoveryResult
) -> None:
    assert (
        list(akcp_sensor.discover_akcp_humidity(akcp_sensor.parse_akcp_humidity(string_table)))
        == expected_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            STRING_TABLE_1,
            "Dual Humidity Port 1",
            [
                Result(state=State.CRIT, summary="State: sensor error"),
                Result(state=State.CRIT, summary="30.00% (warn/crit below 30.00%/35.00%)"),
                Metric("humidity", 30.0, levels=(60.0, 65.0), boundaries=(0.0, 100.0)),
            ],
        ),
        (
            STRING_TABLE_2,
            "Humidity1 Description",
            [Result(state=State.CRIT, summary="State: sensor error")],
        ),
    ],
)
def test_akcp_humidity_check(
    string_table: StringTable, item: str, expected_result: CheckResult
) -> None:
    assert (
        list(
            akcp_sensor.check_akcp_humidity(
                item,
                akcp_sensor.AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS,
                akcp_sensor.parse_akcp_humidity(string_table),
            )
        )
        == expected_result
    )


def test_akcp_temp_discover_keeps_corrupted_row_drops_nameless_one() -> None:
    assert list(
        akcp_sensor.discover_akcp_sensor_temp(akcp_sensor.parse_akcp_temp(TEMP_TABLE_CORRUPTED))
    ) == [Service(item="Temperature 1")]


def test_akcp_temp_check_corrupted_row_goes_stale() -> None:
    assert list(
        akcp_sensor.check_akcp_sensor_temp(
            "Temperature 1",
            akcp_sensor.AKCP_TEMP_CHECK_DEFAULT_PARAMETERS,
            akcp_sensor.parse_akcp_temp(TEMP_TABLE_CORRUPTED),
        )
    ) == [IgnoreResults("Sensor reported corrupted values")]


def test_akcp_relay_discover_keeps_corrupted_row_drops_nameless_one() -> None:
    assert list(
        akcp_sensor.discover_akcp_sensor_relay(akcp_sensor.parse_akcp_water(RELAY_TABLE_CORRUPTED))
    ) == [Service(item="Water Sensor 1")]


def test_akcp_relay_check_corrupted_row_goes_stale() -> None:
    assert list(
        akcp_sensor.check_akcp_sensor_relay(
            "Water Sensor 1",
            akcp_sensor.parse_akcp_water(RELAY_TABLE_CORRUPTED),
        )
    ) == [IgnoreResults("Sensor reported corrupted values")]
