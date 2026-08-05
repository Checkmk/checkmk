#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringByteTable
from cmk.plugins.emka.agent_based.emka_modules import (
    check_emka_modules,
    check_emka_modules_alarm,
    check_emka_modules_handle,
    check_emka_modules_relay,
    check_emka_modules_sensor_humid,
    check_emka_modules_sensor_temp,
    check_emka_modules_sensor_volt,
    ComponentReading,
    discover_emka_modules,
    discover_emka_modules_alarm,
    discover_emka_modules_handle,
    discover_emka_modules_relay,
    discover_emka_modules_sensor_humid,
    discover_emka_modules_sensor_temp,
    discover_emka_modules_sensor_volt,
    EmkaSection,
    ModuleComponent,
    parse_emka_modules,
    SensorReading,
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
    assert section == EmkaSection(
        modules={
            # NOTE: "type" is always "vacant" here regardless of the actual
            # module type -- this reflects a known bug (map_module_types is
            # indexed by co_index, which is always "0" in this branch, instead
            # of by the fetched module-type code). Tracked for a follow-up fix.
            "Master EMKA Master": ModuleComponent(type="vacant", activation="?")
        }
    )


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
    assert section == EmkaSection(
        modules={
            "Perip 1 U11/U32, up to 8 handles / single point latches": ModuleComponent(
                type="vacant",  # see note above -- known bug, always "vacant"
                activation="-",
            )
        }
    )


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
    assert section == EmkaSection(alarms={"MyAlarm 1.1": ComponentReading(value="3")})


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
    assert not section.alarms


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
    assert section == EmkaSection(handles={"MyHandle 1.2": ComponentReading(value="2")})


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
    assert not section.handles


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
    assert section == EmkaSection(relays={"MyRelay 1.4": ComponentReading(value="1")})


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
    assert not section.relays


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
    assert section is not None
    assert section.sensors_temp["TempSensor 1.3"].value == -20.0
    assert section.sensors_temp["TempSensor 1.3"].levels == (-28.2, -28.2)
    assert section.sensors_temp["TempSensor 1.3"].levels_lower == (-29.8, -29.8)


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
    assert section is not None
    assert section.sensors_humid["HumidSensor 1.5"].value == 600.0
    assert section.sensors_humid["HumidSensor 1.5"].levels == (80.0, 80.0)
    assert section.sensors_humid["HumidSensor 1.5"].levels_lower == (20.0, 20.0)


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
    assert section is not None
    assert section.sensors_volt["VoltSensor 1.6"].value == 3300.0
    assert section.sensors_volt["VoltSensor 1.6"].levels == (4000.0, 4000.0)
    assert section.sensors_volt["VoltSensor 1.6"].levels_lower == (2000.0, 2000.0)


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
    assert section is not None
    assert section.sensors_temp["DefaultTemp 1.7"].value == 100.0
    assert section.sensors_temp["DefaultTemp 1.7"].levels == (20.0, 20.0)
    assert section.sensors_temp["DefaultTemp 1.7"].levels_lower == (10.0, 10.0)


def test_discover_emka_modules_skips_inactive() -> None:
    section = EmkaSection(
        modules={
            "Master X": ModuleComponent(type="vacant", activation="i"),
            "Perip 1 Y": ModuleComponent(type="vacant", activation="A"),
        }
    )
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
    section = EmkaSection(modules={"M": ModuleComponent(type="vacant", activation=activation)})
    assert list(check_emka_modules("M", section)) == [expected]


def test_check_emka_modules_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules("does not exist", EmkaSection())) == []


def test_discover_emka_modules_alarm_skips_inactive() -> None:
    section = EmkaSection(
        alarms={
            "A1": ComponentReading(value="2"),
            "A2": ComponentReading(value="3"),
        }
    )
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
    section = EmkaSection(alarms={"A": ComponentReading(value=value)})
    assert list(check_emka_modules_alarm("A", section)) == [expected]


def test_check_emka_modules_alarm_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules_alarm("does not exist", EmkaSection())) == []


def test_discover_emka_modules_handle_all_present_entries() -> None:
    # parse_emka_modules only ever puts entries with a matched value into
    # EmkaSection.handles, so discovery here is unconditional.
    section = EmkaSection(handles={"H1": ComponentReading(value="1")})
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
    section = EmkaSection(handles={"H": ComponentReading(value=value)})
    assert list(check_emka_modules_handle("H", section)) == [expected]


def test_check_emka_modules_handle_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules_handle("does not exist", EmkaSection())) == []


def test_discover_emka_modules_relay_skips_off() -> None:
    section = EmkaSection(
        relays={
            "R1": ComponentReading(value="1"),
            "R2": ComponentReading(value="2"),
        }
    )
    assert list(discover_emka_modules_relay(section)) == [Service(item="R2")]


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", Result(state=State.OK, summary="Status: off")),
        ("2", Result(state=State.OK, summary="Status: on")),
    ],
)
def test_check_emka_modules_relay_states(value: str, expected: Result) -> None:
    section = EmkaSection(relays={"R": ComponentReading(value=value)})
    assert list(check_emka_modules_relay("R", section)) == [expected]


def test_check_emka_modules_relay_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules_relay("does not exist", EmkaSection())) == []


def test_discover_emka_modules_sensor_humid_unconditional() -> None:
    section = EmkaSection(
        sensors_humid={
            "H1": SensorReading(
                value=55.0,
                levels=(70.0, 80.0),
                levels_lower=(20.0, 10.0),
            )
        }
    )
    assert list(discover_emka_modules_sensor_humid(section)) == [Service(item="H1")]


def test_check_emka_modules_sensor_humid() -> None:
    section = EmkaSection(
        sensors_humid={
            "H1": SensorReading(
                value=55.0,
                levels=(70.0, 80.0),
                levels_lower=(20.0, 10.0),
            )
        }
    )
    result = list(check_emka_modules_sensor_humid("H1", {}, section))
    assert result == [
        Result(state=State.OK, summary="55.00%"),
        Metric("humidity", 55.0, boundaries=(0.0, 100.0)),
    ]


def test_check_emka_modules_sensor_humid_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules_sensor_humid("does not exist", {}, EmkaSection())) == []


@pytest.fixture(name="empty_value_store")
def _empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.plugins.emka.agent_based.emka_modules.get_value_store",
        dict,
    )


def test_discover_emka_modules_sensor_temp_unconditional() -> None:
    section = EmkaSection(
        sensors_temp={
            "T1": SensorReading(
                value=-20.0,
                levels=(-28.2, -28.2),
                levels_lower=(-29.8, -29.8),
            )
        }
    )
    assert list(discover_emka_modules_sensor_temp(section)) == [Service(item="T1")]


def test_check_emka_modules_sensor_temp(empty_value_store: None) -> None:
    section = EmkaSection(
        sensors_temp={
            "T1": SensorReading(
                value=-20.0,
                levels=(-28.2, -28.2),
                levels_lower=(-29.8, -29.8),
            )
        }
    )
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


def test_check_emka_modules_sensor_temp_unknown_item_yields_nothing(
    empty_value_store: None,
) -> None:
    assert list(check_emka_modules_sensor_temp("does not exist", {}, EmkaSection())) == []


def test_discover_emka_modules_sensor_volt_unconditional() -> None:
    section = EmkaSection(
        sensors_volt={
            "V1": SensorReading(
                value=3300.0,
                levels=(4000.0, 4000.0),
                levels_lower=(2000.0, 2000.0),
            )
        }
    )
    assert list(discover_emka_modules_sensor_volt(section)) == [Service(item="V1")]


def test_check_emka_modules_sensor_volt_converts_mv_to_v() -> None:
    section = EmkaSection(
        sensors_volt={
            "V1": SensorReading(
                value=3300.0,
                levels=(4000.0, 4000.0),
                levels_lower=(2000.0, 2000.0),
            )
        }
    )
    result = list(check_emka_modules_sensor_volt("V1", {}, section))
    assert result == [
        Result(state=State.OK, summary="Voltage: 3.3 V"),
        Metric("voltage", 3.3),
    ]


def test_check_emka_modules_sensor_volt_unknown_item_yields_nothing() -> None:
    assert list(check_emka_modules_sensor_volt("does not exist", {}, EmkaSection())) == []
