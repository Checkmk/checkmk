#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import assert_never

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EngineeringScientificNotation,
    IECNotation,
    NonConvertibleUnit,
    Notation,
    Precision,
    SINotation,
    StandardScientificNotation,
    StrictPrecision,
    TimeNotation,
    Unit,
)
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.unit_formatter import AutoPrecision as FormatterAutoPrecision
from cmk.gui.unit_formatter import (
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    TimeFormatter,
)
from cmk.gui.unit_formatter import Precision as FormatterPrecision
from cmk.gui.unit_formatter import StrictPrecision as FormatterStrictPrecision
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.shared_typing.cmk_time_series_graph import UnitFormat as SharedUnitFormat


@dataclass(frozen=True)
class UserSpecificUnit:
    formatter: NotationFormatter
    conversion: Callable[[float], float]


@dataclass(frozen=True)
class _Conversion:
    symbol: str
    converter: Callable[[float], float]


def _formatter_precision(precision: Precision) -> FormatterPrecision:
    match precision:
        case AutoPrecision(digits=digits):
            return FormatterAutoPrecision(digits)
        case StrictPrecision(digits=digits):
            return FormatterStrictPrecision(digits)
        case _:
            assert_never(precision)


def _notation_formatter(
    notation: Notation, symbol: str, unit_precision: Precision
) -> NotationFormatter:
    precision = _formatter_precision(unit_precision)
    match notation:
        case DecimalNotation():
            return DecimalFormatter(symbol=symbol, precision=precision)
        case SINotation():
            return SIFormatter(symbol=symbol, precision=precision)
        case IECNotation():
            return IECFormatter(symbol=symbol, precision=precision)
        case StandardScientificNotation():
            return StandardScientificFormatter(symbol=symbol, precision=precision)
        case EngineeringScientificNotation():
            return EngineeringScientificFormatter(symbol=symbol, precision=precision)
        case TimeNotation():
            return TimeFormatter(symbol=symbol, precision=precision)
        case _:
            assert_never(notation)


def formatter_from_unit(unit: Unit | NonConvertibleUnit) -> NotationFormatter:
    return _notation_formatter(unit.notation, unit.notation.symbol, unit.precision)


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
        formatter=_notation_formatter(unit.notation, conversion.symbol, unit.precision),
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


def formatter_from_unit_format(unit_format: SharedUnitFormat) -> NotationFormatter:
    """The formatter for values already in ``unit_format``; it converts nothing."""
    precision: FormatterPrecision = (
        FormatterAutoPrecision(digits=unit_format.precision.digits)
        if unit_format.precision.type == "auto"
        else FormatterStrictPrecision(digits=unit_format.precision.digits)
    )
    symbol = unit_format.symbol
    match unit_format.notation:
        case "decimal":
            return DecimalFormatter(symbol=symbol, precision=precision)
        case "si":
            return SIFormatter(symbol=symbol, precision=precision)
        case "iec":
            return IECFormatter(symbol=symbol, precision=precision)
        case "standard_scientific":
            return StandardScientificFormatter(symbol=symbol, precision=precision)
        case "engineering_scientific":
            return EngineeringScientificFormatter(symbol=symbol, precision=precision)
        case "time":
            return TimeFormatter(symbol=symbol, precision=precision)
        case other:
            assert_never(other)


def user_specific_unit_from_unit_format(
    unit_format: SharedUnitFormat, temperature_unit: TemperatureUnit
) -> UserSpecificUnit:
    converted, conversion = apply_temperature_unit(unit_format, temperature_unit)
    return UserSpecificUnit(formatter=formatter_from_unit_format(converted), conversion=conversion)


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
