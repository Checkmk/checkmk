#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing import unit_to_unit_format
from cmk.gui.graphing._unit_format import apply_temperature_unit
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import Precision, UnitFormat


def test_unit_to_unit_format_decimal_auto_precision() -> None:
    unit = Unit(notation=DecimalNotation("%"), precision=AutoPrecision(2))
    assert unit_to_unit_format(unit) == UnitFormat(
        notation="decimal", symbol="%", precision=Precision(type="auto", digits=2)
    )


def test_unit_to_unit_format_si_strict_precision() -> None:
    unit = Unit(notation=SINotation("B/s"), precision=StrictPrecision(3))
    assert unit_to_unit_format(unit) == UnitFormat(
        notation="si", symbol="B/s", precision=Precision(type="strict", digits=3)
    )


def test_unit_to_unit_format_covers_every_notation() -> None:
    for notation, expected in (
        (IECNotation("B"), "iec"),
        (StandardScientificNotation(""), "standard_scientific"),
        (EngineeringScientificNotation(""), "engineering_scientific"),
        (TimeNotation(), "time"),
    ):
        unit = Unit(notation=notation, precision=AutoPrecision(2))
        assert unit_to_unit_format(unit).notation == expected


def test_apply_temperature_unit_celsius_to_fahrenheit() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(notation="decimal", symbol="°C", precision=Precision(type="auto", digits=2)),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format == UnitFormat(
        notation="decimal",
        symbol="°F",
        precision=Precision(type="auto", digits=2),
        convertible=False,
    )
    assert conversion(20.0) == 68.0


def test_apply_temperature_unit_fahrenheit_to_celsius() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(notation="decimal", symbol="°F", precision=Precision(type="auto", digits=2)),
        TemperatureUnit.CELSIUS,
    )
    assert unit_format.symbol == "°C"
    assert conversion(68.0) == 20.0


def test_apply_temperature_unit_celsius_to_celsius_is_the_identity() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(notation="decimal", symbol="°C", precision=Precision(type="auto", digits=2)),
        TemperatureUnit.CELSIUS,
    )
    assert unit_format.symbol == "°C"
    assert conversion(20.0) == 20.0


def test_apply_temperature_unit_leaves_a_non_temperature_symbol_alone() -> None:
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(notation="si", symbol="B", precision=Precision(type="strict", digits=3)),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format.symbol == "B"
    assert unit_format.precision == Precision(type="strict", digits=3)
    assert conversion(123.456) == 123.456


def test_apply_temperature_unit_respects_a_unit_that_opts_out() -> None:
    # A custom-graph unit whose label merely happens to read "°C" is not a temperature.
    unit_format, conversion = apply_temperature_unit(
        UnitFormat(
            notation="decimal",
            symbol="°C",
            precision=Precision(type="auto", digits=2),
            convertible=False,
        ),
        TemperatureUnit.FAHRENHEIT,
    )
    assert unit_format.symbol == "°C"
    assert conversion(20.0) == 20.0
