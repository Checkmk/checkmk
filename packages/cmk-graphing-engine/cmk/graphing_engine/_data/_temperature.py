#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import assert_never


class TemperatureUnit(enum.Enum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


@dataclass(frozen=True)
class UnitConversion:
    symbol: str
    converter: Callable[[float], float]


def _degree_celsius_conversion(temperature_unit: TemperatureUnit) -> UnitConversion:
    match temperature_unit:
        case TemperatureUnit.CELSIUS:
            return UnitConversion(symbol="°C", converter=lambda c: c)
        case TemperatureUnit.FAHRENHEIT:
            return UnitConversion(symbol="°F", converter=lambda c: c * 1.8 + 32)
        case other:
            assert_never(other)


def _degree_fahrenheit_conversion(temperature_unit: TemperatureUnit) -> UnitConversion:
    match temperature_unit:
        case TemperatureUnit.CELSIUS:
            return UnitConversion(symbol="°C", converter=lambda f: (f - 32) / 1.8)
        case TemperatureUnit.FAHRENHEIT:
            return UnitConversion(symbol="°F", converter=lambda f: f)
        case other:
            assert_never(other)


_TEMPERATURE_CONVERSION_COMPUTER: Mapping[str, Callable[[TemperatureUnit], UnitConversion]] = {
    "°C": _degree_celsius_conversion,
    "°F": _degree_fahrenheit_conversion,
}


def temperature_conversion(
    symbol: str, temperature_unit: TemperatureUnit, fallback: UnitConversion
) -> UnitConversion:
    if (compute_conversion := _TEMPERATURE_CONVERSION_COMPUTER.get(symbol)) is None:
        return fallback
    return compute_conversion(temperature_unit)
