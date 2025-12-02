#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Result, State
from cmk.base.legacy_checks.ucs_c_rack_server_led import (
    check_ucs_c_rack_server_led,
    discover_ucs_c_rack_server_led,
    parse_ucs_c_rack_server_led,
)


def test_ucs_c_rack_server_led_discovery() -> None:
    """Test discovery function returns correct items."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-1",
            "name LED_PSU_STATUS",
            "color green",
            "operState on",
        ],
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-2",
            "name LED_PSU_STATUS",
            "color blue",
            "operState on",
        ],
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-3",
            "name LED_PSU_STATUS",
            "color amber",
            "operState on",
        ],
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-4",
            "name LED_PSU_STATUS",
            "color red",
            "operState on",
        ],
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-5",
            "name LED_PSU_STATUS",
            "color orange",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    result = list(discover_ucs_c_rack_server_led(parsed))

    # Should discover 5 LED items
    assert len(result) == 5
    expected_items = {
        "Rack Unit 1 1",
        "Rack Unit 1 2",
        "Rack Unit 1 3",
        "Rack Unit 1 4",
        "Rack Unit 1 5",
    }
    discovered_items = {service.item for service in result}
    assert discovered_items == expected_items


def test_ucs_c_rack_server_led_check_green() -> None:
    """Test check function for green LED."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-1",
            "name LED_PSU_STATUS",
            "color green",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    params = {
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    }

    result = list(check_ucs_c_rack_server_led("Rack Unit 1 1", params, parsed))
    assert result == [
        Result(state=State.OK, summary="Color: green"),
        Result(state=State.OK, summary="Name: LED_PSU_STATUS"),
        Result(state=State.OK, summary="Operational state: on"),
    ]


def test_ucs_c_rack_server_led_check_amber() -> None:
    """Test check function for amber LED (warning state)."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-3",
            "name LED_PSU_STATUS",
            "color amber",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    params = {
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    }

    result = list(check_ucs_c_rack_server_led("Rack Unit 1 3", params, parsed))
    assert result == [
        Result(state=State.WARN, summary="Color: amber"),
        Result(state=State.OK, summary="Name: LED_PSU_STATUS"),
        Result(state=State.OK, summary="Operational state: on"),
    ]


def test_ucs_c_rack_server_led_check_red() -> None:
    """Test check function for red LED (critical state)."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-4",
            "name LED_PSU_STATUS",
            "color red",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    params = {
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    }

    result = list(check_ucs_c_rack_server_led("Rack Unit 1 4", params, parsed))
    assert result == [
        Result(state=State.CRIT, summary="Color: red"),
        Result(state=State.OK, summary="Name: LED_PSU_STATUS"),
        Result(state=State.OK, summary="Operational state: on"),
    ]


def test_ucs_c_rack_server_led_check_orange() -> None:
    """Test check function for orange LED (unknown state)."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-5",
            "name LED_PSU_STATUS",
            "color orange",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    params = {
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    }

    result = list(check_ucs_c_rack_server_led("Rack Unit 1 5", params, parsed))
    assert result == [
        Result(state=State.UNKNOWN, summary="Color: orange"),
        Result(state=State.OK, summary="Name: LED_PSU_STATUS"),
        Result(state=State.OK, summary="Operational state: on"),
    ]


def test_ucs_c_rack_server_led_parse_function() -> None:
    """Test that parse function works correctly."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-1",
            "name LED_PSU_STATUS",
            "color green",
            "operState on",
        ],
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-2",
            "name LED_TEMP_STATUS",
            "color blue",
            "operState off",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)

    # Should have both LEDs parsed
    assert "Rack Unit 1 1" in parsed
    assert "Rack Unit 1 2" in parsed

    # Check LED 1 data
    led1 = parsed["Rack Unit 1 1"]
    assert led1["Name"] == "LED_PSU_STATUS"
    assert led1["Color"] == "green"
    assert led1["Operational state"] == "on"

    # Check LED 2 data
    led2 = parsed["Rack Unit 1 2"]
    assert led2["Name"] == "LED_TEMP_STATUS"
    assert led2["Color"] == "blue"
    assert led2["Operational state"] == "off"


def test_ucs_c_rack_server_led_discovery_empty_section() -> None:
    """Test discovery with empty data."""
    string_table: list[list[str]] = []

    parsed = parse_ucs_c_rack_server_led(string_table)
    result = list(discover_ucs_c_rack_server_led(parsed))

    assert result == []


def test_ucs_c_rack_server_led_check_missing_item() -> None:
    """Test check function with missing item."""
    string_table = [
        [
            "equipmentIndicatorLed",
            "dn sys/rack-unit-1/indicator-led-1",
            "name LED_PSU_STATUS",
            "color green",
            "operState on",
        ],
    ]

    parsed = parse_ucs_c_rack_server_led(string_table)
    params = {"green": 0}

    result = list(check_ucs_c_rack_server_led("NonExistentItem", params, parsed))

    # Should return empty result for missing item
    assert result == []
