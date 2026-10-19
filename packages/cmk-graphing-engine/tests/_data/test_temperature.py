#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import temperature_conversion, TemperatureUnit, UnitConversion

_UNCONVERTED = UnitConversion(symbol="B", converter=lambda value: value)


def test_degrees_celsius_convert_to_fahrenheit() -> None:
    conversion = temperature_conversion("°C", TemperatureUnit.FAHRENHEIT, _UNCONVERTED)
    assert (conversion.symbol, conversion.converter(100.0)) == ("°F", 212.0)


def test_degrees_fahrenheit_convert_to_celsius() -> None:
    conversion = temperature_conversion("°F", TemperatureUnit.CELSIUS, _UNCONVERTED)
    assert (conversion.symbol, conversion.converter(212.0)) == ("°C", 100.0)


def test_a_unit_without_a_temperature_keeps_the_fallback() -> None:
    assert temperature_conversion("B", TemperatureUnit.FAHRENHEIT, _UNCONVERTED) is _UNCONVERTED
