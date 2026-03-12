#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v1 import Metric, Result, State
from cmk.plugins.lib.temperature import TempParamDict
from cmk.plugins.roomalert.agent_based.ra32e_sensors import (
    _check_ra32e_temperature_sensors,
    check_ra32e_humidity_sensors,
    check_ra32e_power_sensors,
    check_ra32e_sensors_voltage,
    DigitalSection,
    InternalSection,
    parse_ra32e_digital_sensors,
    parse_ra32e_internal_sensors,
)


def test_parse_ra32e_internal_section_temperature() -> None:
    section = parse_ra32e_internal_sensors([["3000", "8000", "5000", "", ""]])

    assert section is not None
    assert section.temperature == 30
    assert section.humidity == 80
    assert section.heat_index == 50


def test_parse_ra32e_internal_section_digital_with_temp() -> None:
    section = parse_ra32e_digital_sensors([["4000", "33", "", "", ""]])

    assert section is not None
    assert section.temperature == 40


def test_parse_ra32e_internal_section_digital_with_humidity() -> None:
    section = parse_ra32e_digital_sensors([["4000", "33", "1400", "1500", "15"]])

    assert section is not None
    assert section.humidity == 14


def test_parse_ra32e_internal_section_digital_with_voltage() -> None:
    section = parse_ra32e_digital_sensors([["4000", "33", "5", "1500", ""]])

    assert section is not None
    assert section.voltage == 5


def test_parse_ra32e_internal_section_digital_with_power() -> None:
    section = parse_ra32e_digital_sensors([["4000", "33", "1", "", ""]])

    assert section is not None
    assert section.power


#
def test_check_ra32e_internal_temperature() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    temp_section = InternalSection(temperature=28.0, humidity=50, heat_index=24)
    result = list(_check_ra32e_temperature_sensors(value_store, "Internal", params, temp_section))

    assert result == [
        Metric("temp", 28.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 28.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_ra32e_internal_heat_level() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    temp_section = InternalSection(temperature=28.0, humidity=50, heat_index=24.0)
    result = list(_check_ra32e_temperature_sensors(value_store, "Heat Index", params, temp_section))

    assert result == [
        Metric("temp", 24.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 24.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_ra32e_digital_temperature() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    internal = InternalSection(temperature=28.0, humidity=50, heat_index=24.0)
    digital = DigitalSection(temperature=27.0, humidity=50, heat_index=23.0)
    result = list(
        _check_ra32e_temperature_sensors(value_store, "Sensor 1", params, internal, [digital])
    )

    assert result == [
        Metric("temp", 27.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 27.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_ra32e_digital_heat_index() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    internal = InternalSection(temperature=28.0, humidity=50, heat_index=24.0)
    digital = DigitalSection(temperature=27.0, humidity=50, heat_index=23.0)
    result = list(
        _check_ra32e_temperature_sensors(value_store, "Heat Index 1", params, internal, [digital])
    )

    assert result == [
        Metric("temp", 23.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 23.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_check_ra32e_temperature_secondary_sections_handled_correctly() -> None:
    value_store: MutableMapping[str, object] = {}
    params: TempParamDict = {"levels": (30.0, 35.0)}
    internal = InternalSection(temperature=28.0, humidity=50, heat_index=24.0)
    digital1 = DigitalSection(temperature=27.0, humidity=50, heat_index=23.0)
    digital2 = DigitalSection(temperature=26.0, humidity=50, heat_index=22.0)
    result1 = list(
        _check_ra32e_temperature_sensors(
            value_store, "Sensor 2", params, internal, [digital1, digital2]
        )
    )
    result2 = list(
        _check_ra32e_temperature_sensors(
            value_store, "Heat Index 2", params, internal, [digital1, digital2]
        )
    )

    assert result1 == [
        Metric("temp", 26.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 26.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]

    assert result2 == [
        Metric("temp", 22.0, levels=(30.0, 35.0)),
        Result(state=State.OK, summary="Temperature: 22.0 °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]


def test_ra32e_digital_sensor_humidity_internal_only() -> None:
    params = {
        "levels": (70.0, 80.0),
    }
    internal = InternalSection(temperature=45, humidity=67, heat_index=40)

    result = list(
        check_ra32e_humidity_sensors(
            "Internal", params, internal, None, None, None, None, None, None, None, None
        )
    )

    assert result == [
        Result(state=State.OK, summary="67.00%"),
        Metric("humidity", 67.0, levels=(70.0, 80.0), boundaries=(0.0, 100.0)),
    ]


def test_ra32e_digital_sensor_humidity_internal_and_digital() -> None:
    params = {
        "levels": (70.0, 80.0),
    }
    internal = InternalSection(temperature=45, humidity=67, heat_index=40)
    digital = DigitalSection(humidity=65, temperature=30)

    result = list(
        check_ra32e_humidity_sensors(
            "Sensor 1", params, internal, digital, None, None, None, None, None, None, None
        )
    )

    assert result == [
        Result(state=State.OK, summary="65.00%"),
        Metric("humidity", 65.0, levels=(70.0, 80.0), boundaries=(0.0, 100.0)),
    ]


def test_ra32e_digital_sensor_voltage() -> None:
    params = {
        "levels": (4, 6),
    }
    section = DigitalSection(temperature=30, voltage=5)
    result = list(
        check_ra32e_sensors_voltage(
            "Sensor 1", params, section, None, None, None, None, None, None, None
        )
    )

    assert result == [
        Result(state=State.OK, summary="Voltage: 5.0 V"),
        Metric("voltage", 5.0),
        Result(state=State.OK, summary="Voltage reading"),
    ]


def test_ra3s_digital_sensor_power() -> None:
    params: Mapping[str, object] = {}
    section = DigitalSection(temperature=30, power=True)
    result = list(
        check_ra32e_power_sensors(
            "Sensor 1", params, section, None, None, None, None, None, None, None
        )
    )

    assert result == [Result(state=State.OK, summary="Device status: power detected(0)")]
