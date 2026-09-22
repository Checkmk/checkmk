#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.apc_inrow_temp import (
    check_apc_inrow_temp,
    inventory_apc_inrow_temp,
    parse_apc_inrow_temp,
)

from cmk.agent_based.v2 import StringTable

# InRow RC of the first generation: airIRRC objects only
AIR_IRRC: list[StringTable] = [[["197", "202", "219", "131", "154"]], [], []]

# InRow ACRC301S: no airIRRC objects, generic coolingUnit tables only
COOLING_UNIT: list[StringTable] = [
    [],
    [
        ["Supply Air Temperature", "607", "F", "10"],
        ["Supply Air Temperature", "159", "C", "10"],
        ["Return Air Temperature", "266", "C", "10"],
        ["Rack Inlet Temperature 1", "192", "C", "10"],
        ["Rack Inlet Temperature 2", "", "C", "10"],
        ["Airflow", "412", "L/s", "1"],
        ["Fan Speed", "30", "%", "1"],
    ],
    [
        ["Entering Chilled Water Temperature", "134", "C", "10"],
        ["Chilled Water Flow", "4", "L/s", "10"],
    ],
]


def test_air_irrc_values_are_tenths_of_degrees() -> None:
    assert parse_apc_inrow_temp(AIR_IRRC) == {
        "Rack Inlet": 19.7,
        "Supply Air": 20.2,
        "Return Air": 21.9,
        "Entering Fluid": 13.1,
        "Leaving Fluid": 15.4,
    }


def test_cooling_unit_tables_are_ignored_if_air_irrc_is_present() -> None:
    assert parse_apc_inrow_temp([AIR_IRRC[0], *COOLING_UNIT[1:]]) == parse_apc_inrow_temp(AIR_IRRC)


def test_cooling_unit_tables_are_used_if_air_irrc_is_unset() -> None:
    assert parse_apc_inrow_temp([[["-1", "-1", "-1", "-1", "-1"]], *COOLING_UNIT[1:]]) == (
        parse_apc_inrow_temp(COOLING_UNIT)
    )


def test_discover_equipped_celsius_sensors_of_cooling_unit() -> None:
    assert list(inventory_apc_inrow_temp(parse_apc_inrow_temp(COOLING_UNIT))) == [
        ("Supply Air", {}),
        ("Return Air", {}),
        ("Rack Inlet 1", {}),
        ("Entering Chilled Water", {}),
    ]


def test_check_applies_scale_of_cooling_unit_reading() -> None:
    assert check_apc_inrow_temp(
        "Supply Air", {"levels": (30.0, 35.0)}, parse_apc_inrow_temp(COOLING_UNIT)
    ) == (0, "15.9 °C", [("temp", 15.9, 30.0, 35.0)])
