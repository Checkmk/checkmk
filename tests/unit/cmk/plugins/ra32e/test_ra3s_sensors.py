#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v1 import Metric, Result, State
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.ra32e.agent_based.ra3s_sensors import (
    _check_ra3s_temperature,
    check_ra3s_humidity,
    check_ra3s_power,
    check_ra3s_voltage,
    DigitalSection,
    DigitalSensorType,
    InternalSection,
    parse_ra3s_digital,
    parse_ra3s_internal_section_temperature,
)


def test_parse_ra3s_internal_section_temperature() -> None:
    section = parse_ra3s_internal_section_temperature([["3000"]])

    assert section is not None
    assert section.temp_celsius == 30


def test_parse_ra3s_digital_with_temp() -> None:
    # missing values are represented with an empty string
    section = parse_ra3s_digital([["4000", "33", "", "", "", ""]])

    assert section is not None
    assert section.sensor_type == DigitalSensorType.TEMP
    assert section.temperature == 40


def test_parse_ra3s_digital_with_humidity() -> None:
    section = parse_ra3s_digital([["4000", "33", "1400", "1500", "15", "20"]])

    assert section is not None
    assert section.sensor_type == DigitalSensorType.TEMP_HUMIDITY
    assert section.humidity == 14


def test_parse_ra3s_digital_with_voltage() -> None:
    section = parse_ra3s_digital([["4000", "33", "5", "1500", ""]])

    assert section is not None
    assert section.sensor_type == DigitalSensorType.TEMP_ANALOG
    assert section.voltage == 5


def test_parse_ra3s_digital_with_power() -> None:
    section = parse_ra3s_digital([["4000", "33", "1", "", "", ""]])

    assert section is not None
    assert section.sensor_type == DigitalSensorType.TEMP_ACTIVE_POWER
    assert section.power_detected == 1


def test_check_ra3s_internal_temperature() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    temp_section = InternalSection(temp_celsius=28)
    result = list(_check_ra3s_temperature(value_store, "Internal", params, temp_section, None))

    assert result == [
        Metric("temp", 28.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 28 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_ra3s_digital_sensor_humidity() -> None:
    params = {
        "levels": (70.0, 80.0),
    }
    section = DigitalSection(
        sensor_type=DigitalSensorType.TEMP_HUMIDITY,
        temperature=30,
        humidity=65,
    )
    result = list(check_ra3s_humidity("Sensor", params, section))

    assert result == [
        Result(state=State.OK, summary="65.00%"),
        Metric("humidity", 65.0, levels=(70.0, 80.0), boundaries=(0.0, 100.0)),
    ]


def test_ra3s_digital_sensor_voltage() -> None:
    params: Mapping[str, object] = {
        "levels": (4, 6),
    }
    section = DigitalSection(
        sensor_type=DigitalSensorType.TEMP_ANALOG,
        temperature=30,
        voltage=5,
    )
    result = list(check_ra3s_voltage("Sensor", params, section))

    assert result == [
        Result(state=State.OK, summary="Voltage: 5.0 V"),
        Metric("voltage", 5.0),
        Result(state=State.OK, summary="Voltage reading"),
    ]


def test_ra3s_digital_sensor_power() -> None:
    params: Mapping[str, object] = {}
    section = DigitalSection(
        sensor_type=DigitalSensorType.TEMP_ACTIVE_POWER,
        temperature=30,
        power_detected=True,
    )
    result = list(check_ra3s_power("Sensor", params, section))

    assert result == [Result(state=State.OK, summary="Device status: power detected(0)")]
