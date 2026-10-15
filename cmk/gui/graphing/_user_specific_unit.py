#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing_engine import NonConvertibleUnit, Unit
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import UnitFormat as SharedUnitFormat
from cmk.web.utils.unit_formatter import notation_formatter, NotationFormatter

from ._unit_format import unit_to_unit_format


@dataclass(frozen=True)
class UserSpecificUnit:
    formatter: NotationFormatter
    conversion: Callable[[float], float]


@dataclass(frozen=True)
class _Conversion:
    symbol: str
    converter: Callable[[float], float]


def user_unit_format(
    unit: Unit | NonConvertibleUnit, temperature_unit: TemperatureUnit
) -> tuple[SharedUnitFormat, Callable[[float], float]]:
    unit_format = unit_to_unit_format(unit)
    noop_conversion = _Conversion(symbol=unit_format.symbol, converter=lambda v: v)
    conversion = (
        _temperature_conversion(unit_format.symbol, temperature_unit, noop_conversion)
        if isinstance(unit, Unit)
        else noop_conversion
    )
    return (
        SharedUnitFormat(
            notation=unit_format.notation,
            symbol=conversion.symbol,
            precision=unit_format.precision,
            convertible=False,
        ),
        conversion.converter,
    )


def user_specific_unit(
    unit: Unit | NonConvertibleUnit,
    temperature_unit: TemperatureUnit,
) -> UserSpecificUnit:
    unit_format, conversion = user_unit_format(unit, temperature_unit)
    return UserSpecificUnit(
        formatter=notation_formatter(
            unit_format.notation,
            unit_format.symbol,
            unit_format.precision.type,
            unit_format.precision.digits,
        ),
        conversion=conversion,
    )


def _degree_celsius_conversion(temperature_unit: TemperatureUnit) -> _Conversion:
    match temperature_unit:
        case TemperatureUnit.CELSIUS:
            return _Conversion(symbol="°C", converter=lambda c: c)
        case TemperatureUnit.FAHRENHEIT:
            return _Conversion(symbol="°F", converter=lambda c: c * 1.8 + 32)
        case other:
            assert_never(other)


def _degree_fahrenheit_conversion(temperature_unit: TemperatureUnit) -> _Conversion:
    match temperature_unit:
        case TemperatureUnit.CELSIUS:
            return _Conversion(symbol="°C", converter=lambda f: (f - 32) / 1.8)
        case TemperatureUnit.FAHRENHEIT:
            return _Conversion(symbol="°F", converter=lambda f: f)
        case other:
            assert_never(other)


_TEMPERATURE_CONVERSION_COMPUTER: Mapping[str, Callable[[TemperatureUnit], _Conversion]] = {
    "°C": _degree_celsius_conversion,
    "°F": _degree_fahrenheit_conversion,
}


def _temperature_conversion(
    symbol: str, temperature_unit: TemperatureUnit, fallback: _Conversion
) -> _Conversion:
    if (compute_conversion := _TEMPERATURE_CONVERSION_COMPUTER.get(symbol)) is None:
        return fallback
    return compute_conversion(temperature_unit)


def get_temperature_unit(user: LoggedInUser, temperature_unit: str) -> TemperatureUnit:
    return TemperatureUnit(user.get_attribute("temperature_unit") or temperature_unit)
