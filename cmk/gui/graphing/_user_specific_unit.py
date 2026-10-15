#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import assert_never

from cmk.graphing_engine import NonConvertibleUnit, notation_name, precision_kind, Unit
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import UnitFormat as SharedUnitFormat
from cmk.web.utils.unit_formatter import notation_formatter, NotationFormatter


@dataclass(frozen=True)
class UserSpecificUnit:
    formatter: NotationFormatter
    conversion: Callable[[float], float]


@dataclass(frozen=True)
class _Conversion:
    symbol: str
    converter: Callable[[float], float]


def user_specific_unit(
    unit: Unit | NonConvertibleUnit,
    temperature_unit: TemperatureUnit,
) -> UserSpecificUnit:
    noop_conversion = _Conversion(
        symbol=unit.notation.symbol,
        converter=lambda v: v,
    )
    conversion = (
        _temperature_conversion(unit.notation.symbol, temperature_unit, noop_conversion)
        if isinstance(unit, Unit)
        else noop_conversion
    )
    return UserSpecificUnit(
        formatter=notation_formatter(
            notation_name(unit.notation),
            conversion.symbol,
            precision_kind(unit.precision),
            unit.precision.digits,
        ),
        conversion=conversion.converter,
    )


def apply_temperature_unit(
    unit_format: SharedUnitFormat, temperature_unit: TemperatureUnit
) -> tuple[SharedUnitFormat, Callable[[float], float]]:
    """Unit and converter as a pair, so no caller relabels values without converting them.

    ``convertible=False`` tells the frontend the numbers are already converted."""
    noop_conversion = _Conversion(symbol=unit_format.symbol, converter=lambda v: v)
    conversion = (
        _temperature_conversion(unit_format.symbol, temperature_unit, noop_conversion)
        if unit_format.convertible is not False
        else noop_conversion
    )
    return (
        replace(unit_format, symbol=conversion.symbol, convertible=False),
        conversion.converter,
    )


def user_specific_unit_from_unit_format(
    unit_format: SharedUnitFormat, temperature_unit: TemperatureUnit
) -> UserSpecificUnit:
    converted, conversion = apply_temperature_unit(unit_format, temperature_unit)
    return UserSpecificUnit(
        formatter=notation_formatter(
            converted.notation,
            converted.symbol,
            converted.precision.type,
            converted.precision.digits,
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
