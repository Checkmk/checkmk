#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import assert_never, Literal

from pydantic import BaseModel, Field

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._formatter import (
    AutoPrecision,
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    NotationFormatter,
    SIFormatter,
    StandardScientificFormatter,
    StrictPrecision,
    TimeFormatter,
)


class DecimalNotation(BaseModel, frozen=True):
    type: Literal["decimal"] = "decimal"
    symbol: str


class SINotation(BaseModel, frozen=True):
    type: Literal["si"] = "si"
    symbol: str


class IECNotation(BaseModel, frozen=True):
    type: Literal["iec"] = "iec"
    symbol: str


class StandardScientificNotation(BaseModel, frozen=True):
    type: Literal["standard_scientific"] = "standard_scientific"
    symbol: str


class EngineeringScientificNotation(BaseModel, frozen=True):
    type: Literal["engineering_scientific"] = "engineering_scientific"
    symbol: str


class TimeNotation(BaseModel, frozen=True):
    type: Literal["time"] = "time"
    symbol: str


class ConvertibleUnitSpecification(BaseModel, frozen=True):
    type: Literal["convertible"] = "convertible"
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    ) = Field(
        ...,
        discriminator="type",
    )
    precision: AutoPrecision | StrictPrecision = Field(
        ...,
        discriminator="type",
    )


class NonConvertibleUnitSpecification(BaseModel, frozen=True):
    type: Literal["non_convertible"] = "non_convertible"
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    ) = Field(
        ...,
        discriminator="type",
    )
    precision: AutoPrecision | StrictPrecision = Field(
        ...,
        discriminator="type",
    )


@dataclass(frozen=True)
class UserSpecificUnit:
    formatter: NotationFormatter
    conversion: Callable[[float], float]


@dataclass(frozen=True)
class _Conversion:
    symbol: str
    converter: Callable[[float], float]


def user_specific_unit(
    unit_specification: ConvertibleUnitSpecification | NonConvertibleUnitSpecification,
    user: LoggedInUser,
    config: Config,
    source_symbol_to_conversion_computer: (
        Mapping[str, Callable[[LoggedInUser, Config], _Conversion]] | None
    ) = None,
) -> UserSpecificUnit:
    noop_conversion = _Conversion(
        symbol=unit_specification.notation.symbol,
        converter=lambda v: v,
    )
    conversion = (
        (source_symbol_to_conversion_computer or _TEMPERATURE_CONVERSION_COMPUTER).get(
            unit_specification.notation.symbol,
            lambda *_: noop_conversion,
        )(user, config)
        if isinstance(unit_specification, ConvertibleUnitSpecification)
        else noop_conversion
    )
    formatter: NotationFormatter
    match unit_specification.notation:
        case DecimalNotation():
            formatter = DecimalFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case SINotation():
            formatter = SIFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case IECNotation():
            formatter = IECFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case StandardScientificNotation():
            formatter = StandardScientificFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case EngineeringScientificNotation():
            formatter = EngineeringScientificFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case TimeNotation():
            formatter = TimeFormatter(
                symbol=conversion.symbol,
                precision=unit_specification.precision,
            )
        case _:
            assert_never(unit_specification.notation)

    return UserSpecificUnit(
        formatter=formatter,
        conversion=conversion.converter,
    )


def _degree_celsius_conversion(user: LoggedInUser, config: Config) -> _Conversion:
    match configured_temp_unit := TemperatureUnit(
        user.get_attribute("temperature_unit") or config.default_temperature_unit
    ):
        case TemperatureUnit.CELSIUS:
            return _Conversion(symbol="°C", converter=lambda c: c)
        case TemperatureUnit.FAHRENHEIT:
            return _Conversion(symbol="°F", converter=lambda c: c * 1.8 + 32)
        case _:
            assert_never(configured_temp_unit)


def _degree_fahrenheit_conversion(user: LoggedInUser, config: Config) -> _Conversion:
    match configured_temp_unit := TemperatureUnit(
        user.get_attribute("temperature_unit") or config.default_temperature_unit
    ):
        case TemperatureUnit.CELSIUS:
            return _Conversion(symbol="°C", converter=lambda f: (f - 32) / 1.8)
        case TemperatureUnit.FAHRENHEIT:
            return _Conversion(symbol="°F", converter=lambda f: f)
        case _:
            assert_never(configured_temp_unit)


_TEMPERATURE_CONVERSION_COMPUTER: Mapping[str, Callable[[LoggedInUser, Config], _Conversion]] = {
    "°C": _degree_celsius_conversion,
    "°F": _degree_fahrenheit_conversion,
}
