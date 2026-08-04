#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v1 import Metric, Result, Service, State
from cmk.agent_based.v2 import StringByteTable
from cmk.plugins.emka.agent_based.emka_modules import (
    check_emka_modules,
    check_emka_modules_alarm,
    check_emka_modules_handle,
    check_emka_modules_relay,
    check_emka_modules_sensor_humid,
    check_emka_modules_sensor_temp,
    check_emka_modules_sensor_volt,
    discover_emka_modules,
    discover_emka_modules_alarm,
    discover_emka_modules_handle,
    discover_emka_modules_relay,
    discover_emka_modules_sensor_humid,
    discover_emka_modules_sensor_temp,
    discover_emka_modules_sensor_volt,
    parse_emka_modules,
)

# Universal ELM2-MIB scaling equation, ASCII-coded and null-byte separated, as bytes/ints
# (OIDBytes returns list[int]). "=#\xb0C" -> temperature unit marker.
# =#°C, 0.02, -30.0
_EQUATION_TEMP_SCALED = [61, 35, 176, 67, 0, 48, 46, 48, 50, 0, 45, 51, 48, 46, 48, 0]
# =#°C, no multiplier/offset parts -> default (1.0, 0.0)
_EQUATION_TEMP_NO_SCALE = [61, 35, 176, 67, 0]
# =#%RF, 1.0, 0.0
_EQUATION_HUMID_SCALED = [61, 35, 37, 82, 70, 0, 49, 46, 48, 0, 48, 46, 48, 0]
# =V, 1.0, 0.0
_EQUATION_VOLT_SCALED = [61, 86, 0, 49, 46, 48, 0, 48, 46, 48, 0]


def test_parse_emka_modules_empty_string_table_returns_none() -> None:
    assert parse_emka_modules([[], [], [], [], [], [], []]) is None


def test_parse_emka_modules_master_module() -> None:
    string_table: Sequence[StringByteTable] = [
        [["0.0", "?", "0", "EMKA Master, v1.0", ""]],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {
            "Master EMKA Master": {
                # NOTE: "type" is always "vacant" here regardless of the actual
                # module type — this reflects a known bug (map_module_types is
                # indexed by co_index, which is always "0" in this branch, instead
                # of by the fetched module-type code). Tracked for a follow-up fix.
                "type": "vacant",
                "activation": "?",
                "_location_": "0.0",
            }
        }
    }


def test_parse_emka_modules_peripheral_module() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.0", "-", "11", "U11/U32, up to 8 handles / single point latches", ""]],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {
            "Perip 1 U11/U32, up to 8 handles / single point latches": {
                "type": "vacant",  # see note above — known bug, always "vacant"
                "activation": "-",
                "_location_": "0.1",
            }
        }
    }


def test_parse_emka_modules_alarm_component() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.1", "", "1", "", "MyAlarm"]],
        [["X.1.1", "3", ""]],
        [],
        [],
        [],
        [],
        [],
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "alarm": {"MyAlarm 1.1": {"_location_": "1.1", "value": "3"}},
    }


@pytest.mark.xfail(strict=True, reason="currently parsed without value causing check crash")
def test_parse_emka_modules_alarm_component_without_matching_value_is_omitted() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.1", "", "1", "", "MyAlarm"]],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    assert (section := parse_emka_modules(string_table))
    assert not section["alarm"]


def test_parse_emka_modules_handle_component() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.2", "", "2", "", "MyHandle"]],
        [],
        [["X.1.2", "2", ""]],
        [],
        [],
        [],
        [],
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "handle": {"MyHandle 1.2": {"_location_": "1.2", "value": "2"}},
    }


@pytest.mark.xfail(strict=True, reason="currently parsed without value causing check crash")
def test_parse_emka_modules_handle_component_without_matching_value_is_omitted() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.2", "", "2", "", "MyHandle"]],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    assert (section := parse_emka_modules(string_table))
    assert not section["handle"]


def test_parse_emka_modules_relay_component() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.4", "", "4", "", "MyRelay"]],
        [],
        [],
        [],
        [["X.1.4", "1", ""]],
        [],
        [],
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "relay": {"MyRelay 1.4": {"_location_": "1.4", "value": "1"}},
    }


@pytest.mark.xfail(strict=True, reason="currently parsed without value causing check crash")
def test_parse_emka_modules_relay_component_without_matching_value_is_omitted() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.4", "", "4", "", "MyRelay"]],
        [],
        [],
        [],
        [],
        [],
        [],
    ]
    assert (section := parse_emka_modules(string_table))
    assert not section["relay"]


def test_parse_emka_modules_sensor_temp_with_thresholds_and_scaling() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.3", "", "3", "", "TempSensor"]],
        [],
        [],
        [["Y.1.3", "500", ""]],
        [],
        [["1.1", "10"], ["1.2", "90"]],
        [["51.0", _EQUATION_TEMP_SCALED]],  # chr(51) == "3", matches sensor location "1.3"
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "sensor_temp": {
            "TempSensor 1.3": {
                "value": -20.0,
                "levels": [-28.2, -28.2],
                "levels_lower": [-29.8, -29.8],
            }
        },
    }


def test_parse_emka_modules_sensor_humid_with_thresholds_and_scaling() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.5", "", "3", "", "HumidSensor"]],
        [],
        [],
        [["Y.1.5", "600", ""]],
        [],
        [["1.1", "20"], ["1.2", "80"]],
        [["53.0", _EQUATION_HUMID_SCALED]],  # chr(53) == "5", matches sensor location "1.5"
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "sensor_humid": {
            "HumidSensor 1.5": {
                "value": 600.0,
                "levels": [80.0, 80.0],
                "levels_lower": [20.0, 20.0],
            }
        },
    }


def test_parse_emka_modules_sensor_volt_with_thresholds_and_scaling() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.6", "", "3", "", "VoltSensor"]],
        [],
        [],
        [["Y.1.6", "3300", ""]],
        [],
        [["1.1", "2000"], ["1.2", "4000"]],
        [["54.0", _EQUATION_VOLT_SCALED]],  # chr(54) == "6", matches sensor location "1.6"
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "sensor_volt": {
            "VoltSensor 1.6": {
                "value": 3300.0,
                "levels": [4000.0, 4000.0],
                "levels_lower": [2000.0, 2000.0],
            }
        },
    }


def test_parse_emka_modules_sensor_scaling_defaults_without_multiplier_offset() -> None:
    string_table: Sequence[StringByteTable] = [
        [["1.7", "", "3", "", "DefaultTemp"]],
        [],
        [],
        [["Y.1.7", "100", ""]],
        [],
        [["1.1", "10"], ["1.2", "20"]],
        [["55.0", _EQUATION_TEMP_NO_SCALE]],  # chr(55) == "7", matches sensor location "1.7"
    ]
    section = parse_emka_modules(string_table)
    assert section == {
        "basic_components": {},
        "sensor_temp": {
            "DefaultTemp 1.7": {
                "value": 100.0,
                "levels": [20.0, 20.0],
                "levels_lower": [10.0, 10.0],
            }
        },
    }


def test_discover_emka_modules_skips_inactive() -> None:
    section = {
        "basic_components": {
            "Master X": {"type": "vacant", "activation": "i", "_location_": "0.0"},
            "Perip 1 Y": {"type": "vacant", "activation": "A", "_location_": "0.1"},
        }
    }
    assert list(discover_emka_modules(section)) == [Service(item="Perip 1 Y")]


@pytest.mark.parametrize(
    "activation, expected",
    [
        ("-", Result(state=State.OK, summary="Activation status: vacant, Type: vacant")),
        ("?", Result(state=State.OK, summary="Activation status: detect modus, Type: vacant")),
        ("x", Result(state=State.OK, summary="Activation status: excluded, Type: vacant")),
        ("e", Result(state=State.CRIT, summary="Activation status: error, Type: vacant")),
        (
            "c",
            Result(state=State.CRIT, summary="Activation status: collision detected, Type: vacant"),
        ),
        (
            "w",
            Result(
                state=State.WARN,
                summary="Activation status: wait for dynamic address, Type: vacant",
            ),
        ),
        ("P", Result(state=State.WARN, summary="Activation status: polling, Type: vacant")),
        ("i", Result(state=State.OK, summary="Activation status: inactive, Type: vacant")),
        ("t", Result(state=State.CRIT, summary="Activation status: timeout, Type: vacant")),
        ("T", Result(state=State.CRIT, summary="Activation status: timeout alarm, Type: vacant")),
        ("A", Result(state=State.CRIT, summary="Activation status: alarm active, Type: vacant")),
        ("L", Result(state=State.OK, summary="Activation status: alarm latched, Type: vacant")),
        ("#", Result(state=State.OK, summary="Activation status: OK, Type: vacant")),
    ],
)
def test_check_emka_modules_activation_states(activation: str, expected: Result) -> None:
    section = {
        "basic_components": {"M": {"type": "vacant", "activation": activation, "_location_": "0.1"}}
    }
    assert list(check_emka_modules("M", section)) == [expected]


def test_discover_emka_modules_alarm_skips_inactive() -> None:
    section = {
        "alarm": {
            "A1": {"_location_": "1.1", "value": "2"},
            "A2": {"_location_": "1.2", "value": "3"},
        }
    }
    assert list(discover_emka_modules_alarm(section)) == [Service(item="A2")]


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", Result(state=State.UNKNOWN, summary="Status: unknown")),
        ("2", Result(state=State.OK, summary="Status: inactive")),
        ("3", Result(state=State.CRIT, summary="Status: active")),
        ("4", Result(state=State.OK, summary="Status: latched")),
    ],
)
def test_check_emka_modules_alarm_states(value: str, expected: Result) -> None:
    section = {"alarm": {"A": {"_location_": "1.1", "value": value}}}
    assert list(check_emka_modules_alarm("A", section)) == [expected]


def test_discover_emka_modules_handle_on_value_presence() -> None:
    section = {
        "handle": {
            "H1": {"_location_": "1.1", "value": "1"},
            "H2": {"_location_": "1.2"},  # no "value" key -> not discovered
        }
    }
    assert list(discover_emka_modules_handle(section)) == [Service(item="H1")]


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", Result(state=State.OK, summary="Status: closed")),
        ("2", Result(state=State.WARN, summary="Status: opened")),
        ("3", Result(state=State.UNKNOWN, summary="Status: unlocked")),
        ("4", Result(state=State.UNKNOWN, summary="Status: delay")),
        ("5", Result(state=State.CRIT, summary="Status: open time ex")),
    ],
)
def test_check_emka_modules_handle_states(value: str, expected: Result) -> None:
    section = {"handle": {"H": {"_location_": "1.1", "value": value}}}
    assert list(check_emka_modules_handle("H", section)) == [expected]


def test_discover_emka_modules_relay_skips_off() -> None:
    section = {
        "relay": {
            "R1": {"_location_": "1.1", "value": "1"},
            "R2": {"_location_": "1.2", "value": "2"},
        }
    }
    assert list(discover_emka_modules_relay(section)) == [Service(item="R2")]


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", Result(state=State.OK, summary="Status: off")),
        ("2", Result(state=State.OK, summary="Status: on")),
    ],
)
def test_check_emka_modules_relay_states(value: str, expected: Result) -> None:
    section = {"relay": {"R": {"_location_": "1.1", "value": value}}}
    assert list(check_emka_modules_relay("R", section)) == [expected]


def test_discover_emka_modules_sensor_temp_unconditional() -> None:
    section = {
        "sensor_temp": {
            "T1": {"value": -20.0, "levels": [-28.2, -28.2], "levels_lower": [-29.8, -29.8]}
        }
    }
    assert list(discover_emka_modules_sensor_temp(section)) == [Service(item="T1")]


@pytest.fixture(name="empty_value_store")
def _empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.emka.agent_based.emka_modules.get_value_store",
        dict,
    )


def test_check_emka_modules_sensor_temp(empty_value_store: None) -> None:
    section = {
        "sensor_temp": {
            "T1": {"value": -20.0, "levels": [-28.2, -28.2], "levels_lower": [-29.8, -29.8]}
        }
    }
    result = list(check_emka_modules_sensor_temp("T1", {}, section))
    assert result == [
        Metric("temp", -20.0, levels=(-28.2, -28.2)),
        Result(
            state=State.CRIT,
            summary="Temperature: -20.0 \xb0C (warn/crit at -28.2 \xb0C/-28.2 \xb0C)",
        ),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


def test_discover_emka_modules_sensor_humid_unconditional() -> None:
    section = {"sensor_humid": {"H1": {"value": 55.0}}}
    assert list(discover_emka_modules_sensor_humid(section)) == [Service(item="H1")]


def test_check_emka_modules_sensor_humid() -> None:
    section = {"sensor_humid": {"H1": {"value": 55.0}}}
    result = list(check_emka_modules_sensor_humid("H1", {}, section))
    assert result == [
        Result(state=State.OK, summary="55.00%"),
        Metric("humidity", 55.0, boundaries=(0.0, 100.0)),
    ]


def test_discover_emka_modules_sensor_volt_unconditional() -> None:
    section = {"sensor_volt": {"V1": {"value": 3300.0}}}
    assert list(discover_emka_modules_sensor_volt(section)) == [Service(item="V1")]


def test_check_emka_modules_sensor_volt_converts_mv_to_v() -> None:
    section = {"sensor_volt": {"V1": {"value": 3300.0}}}
    result = list(check_emka_modules_sensor_volt("V1", {}, section))
    assert result == [
        Result(state=State.OK, summary="Voltage: 3.3 V"),
        Metric("voltage", 3.3),
    ]
