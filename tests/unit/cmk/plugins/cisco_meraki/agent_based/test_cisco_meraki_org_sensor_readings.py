#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from zoneinfo import ZoneInfo

import pytest
import time_machine
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_sensor_readings import (
    check_sensor_battery,
    check_sensor_humidity,
    check_sensor_temperature,
    discover_sensor_temperature,
    parse_sensor_readings,
)
from cmk.plugins.cisco_meraki.lib.schema import RawSensorReadings


class _RawSensorReadingsFactory(TypedDictFactory[RawSensorReadings]):
    __check_model__ = False


def test_discover_sensor_temperature() -> None:
    sensor_reading = _RawSensorReadingsFactory.build(readings=[{"metric": "temperature"}])
    string_table = [[f"[{json.dumps(sensor_reading)}]"]]
    section = parse_sensor_readings(string_table)
    assert section

    value = list(discover_sensor_temperature(section))
    expected = [Service(item="Sensor")]

    assert value == expected


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_sensor_readings.get_value_store",
        lambda: {},
    )


@pytest.mark.usefixtures("empty_value_store")
@time_machine.travel(datetime.datetime(2000, 1, 30, 12, tzinfo=ZoneInfo("UTC")))
def test_check_sensor_temperature() -> None:
    sensor_reading = _RawSensorReadingsFactory.build(
        readings=[
            {
                "ts": "2000-01-14T12:00:00Z",
                "metric": "temperature",
                "temperature": {"fahrenheit": 77.81, "celsius": 23.45},
            },
            {
                "ts": "2000-01-15T12:00:00Z",
                "metric": "temperature",
                "temperature": {"fahrenheit": 77.81, "celsius": 25.45},
            },
        ]
    )
    string_table = [[f"[{json.dumps(sensor_reading)}]"]]
    section = parse_sensor_readings(string_table)
    assert section

    value = list(check_sensor_temperature("Sensor", {}, section))
    expected = [
        Metric("temp", 25.45),
        Result(state=State.OK, summary="Temperature: 25.4 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
        Result(state=State.OK, summary="Time since last report: 15 days 0 hours"),
    ]

    assert value == expected


@pytest.mark.usefixtures("empty_value_store")
def test_check_sensor_temperature_reports_zero_degrees() -> None:
    sensor_reading = _RawSensorReadingsFactory.build(
        readings=[
            {
                "ts": "2000-01-15T12:00:00Z",
                "metric": "temperature",
                "temperature": {"fahrenheit": 32.0, "celsius": 0.0},
            },
        ]
    )
    section = parse_sensor_readings([[f"[{json.dumps(sensor_reading)}]"]])
    assert section

    value = list(check_sensor_temperature("Sensor", {"levels_lower": (5.0, 2.0)}, section))

    assert (
        Result(state=State.CRIT, summary="Temperature: 0.0 °C (warn/crit below 5.0 °C/2.0 °C)")
        in value
    )


def test_check_sensor_battery_reports_empty_battery() -> None:
    sensor_reading = _RawSensorReadingsFactory.build(
        readings=[
            {
                "ts": "2000-01-15T12:00:00Z",
                "metric": "battery",
                "battery": {"percentage": 0},
            },
        ]
    )
    section = parse_sensor_readings([[f"[{json.dumps(sensor_reading)}]"]])
    assert section

    value = list(check_sensor_battery("Sensor", {"levels_lower": (20, 10)}, section))

    assert Result(state=State.CRIT, summary="0% (warn/crit below 20.00%/10.00%)") in value


def test_check_sensor_humidity_reports_zero_percent() -> None:
    sensor_reading = _RawSensorReadingsFactory.build(
        readings=[
            {
                "ts": "2000-01-15T12:00:00Z",
                "metric": "humidity",
                "humidity": {"relativePercentage": 0},
            },
        ]
    )
    section = parse_sensor_readings([[f"[{json.dumps(sensor_reading)}]"]])
    assert section

    value = list(check_sensor_humidity("Sensor", {"levels_lower": (20.0, 10.0)}, section))

    assert Result(state=State.CRIT, summary="0% (warn/crit below 20.00%/10.00%)") in value
