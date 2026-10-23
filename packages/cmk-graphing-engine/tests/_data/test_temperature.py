#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    NonConvertibleUnit,
    TemperatureUnit,
    Unit,
    unit_conversion,
)


def _celsius() -> Unit:
    return Unit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))


def test_degrees_celsius_convert_to_fahrenheit() -> None:
    conversion = unit_conversion(_celsius(), TemperatureUnit.FAHRENHEIT)
    assert (conversion.symbol, conversion.converter(100.0)) == ("°F", 212.0)


def test_degrees_fahrenheit_convert_to_celsius() -> None:
    fahrenheit = Unit(notation=DecimalNotation("°F"), precision=AutoPrecision(2))
    conversion = unit_conversion(fahrenheit, TemperatureUnit.CELSIUS)
    assert (conversion.symbol, conversion.converter(212.0)) == ("°C", 100.0)


def test_a_unit_without_a_temperature_keeps_its_values() -> None:
    bytes_unit = Unit(notation=DecimalNotation("B"), precision=AutoPrecision(2))
    conversion = unit_conversion(bytes_unit, TemperatureUnit.FAHRENHEIT)
    assert (conversion.symbol, conversion.converter(3.0)) == ("B", 3.0)


def test_a_non_convertible_unit_keeps_its_values() -> None:
    unit = NonConvertibleUnit(notation=DecimalNotation("°C"), precision=AutoPrecision(2))
    conversion = unit_conversion(unit, TemperatureUnit.FAHRENHEIT)
    assert (conversion.symbol, conversion.converter(100.0)) == ("°C", 100.0)
