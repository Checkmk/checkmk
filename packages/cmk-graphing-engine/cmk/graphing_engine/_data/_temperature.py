#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable
from dataclasses import dataclass

from ._units import NonConvertibleUnit, Unit


class TemperatureUnit(enum.Enum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


@dataclass(frozen=True)
class UnitConversion:
    symbol: str
    converter: Callable[[float], float]


def unit_conversion(
    unit: Unit | NonConvertibleUnit, temperature_unit: TemperatureUnit
) -> UnitConversion:
    match unit, unit.notation.symbol, temperature_unit:
        case Unit(), "°C", TemperatureUnit.FAHRENHEIT:
            return UnitConversion(symbol="°F", converter=lambda c: c * 1.8 + 32)
        case Unit(), "°F", TemperatureUnit.CELSIUS:
            return UnitConversion(symbol="°C", converter=lambda f: (f - 32) / 1.8)
        case _:
            return UnitConversion(symbol=unit.notation.symbol, converter=lambda value: value)
