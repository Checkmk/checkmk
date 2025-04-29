#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based import cisco_meraki_org_sensor_readings

_STRING_TABLE = [
    [
        (
            '[{"serial": "Q234-ABCD-5678", "network": {"id": "N_24329156", "name": "Main Office"},'
            ' "readings": [{"ts": "2000-01-14T12:00:00Z", "metric": "temperature",'
            ' "temperature": {"fahrenheit": 77.81, "celsius": 23.45},'
            ' "humidity": {"relativePercentage": 34}, "water": {"present": true},'
            ' "door": {"open": true}, "tvoc": {"concentration": 100},'
            ' "pm25": {"concentration": 100}, "noise": {"ambient": {"level": 45}},'
            ' "indoorAirQuality": {"score": 89}, "button": {"pressType": "short"},'
            ' "battery": {"percentage": 90}},'
            ' {"ts": "2000-01-15T12:00:00Z", "metric": "temperature",'
            ' "temperature": {"fahrenheit": 77.81, "celsius": 25.45},'
            ' "humidity": {"relativePercentage": 34}, "water": {"present": true},'
            ' "door": {"open": true}, "tvoc": {"concentration": 100},'
            ' "pm25": {"concentration": 100}, "noise": {"ambient": {"level": 45}},'
            ' "indoorAirQuality": {"score": 89}, "button": {"pressType": "short"},'
            ' "battery": {"percentage": 91}}]}]'
        ),
    ]
]


@pytest.mark.parametrize(
    "string_table, expected_services",
    [
        ([], []),
        ([[]], []),
        ([[""]], []),
        (
            _STRING_TABLE,
            [
                Service(item="Sensor"),
            ],
        ),
    ],
)
def test_discover_sensor_temperature(
    string_table: StringTable, expected_services: Sequence[Service]
) -> None:
    section = cisco_meraki_org_sensor_readings.parse_sensor_readings(string_table)
    assert sorted(expected_services) == sorted(
        cisco_meraki_org_sensor_readings.discover_sensor_temperature(section)
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        ([], []),
        ([[]], []),
        ([[""]], []),
        (
            _STRING_TABLE,
            [
                Metric("temp", 25.45),
                Result(state=State.OK, summary="Temperature: 25.4 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
                Result(state=State.OK, summary="Time since last report: 15 days 0 hours"),
            ],
        ),
    ],
)
def test_check_sensor_temperature(
    string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    section = cisco_meraki_org_sensor_readings.parse_sensor_readings(string_table)
    with time_machine.travel(datetime.datetime(2000, 1, 30, 12, tzinfo=ZoneInfo("UTC"))):
        assert (
            list(cisco_meraki_org_sensor_readings.check_sensor_temperature("Sensor", {}, section))
            == expected_results
        )
