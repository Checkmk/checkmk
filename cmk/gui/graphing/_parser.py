#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from dataclasses import dataclass
from typing import Callable, Final, Protocol

from cmk.graphing.v1 import metrics

from ._loader import units_from_api
from ._type_defs import UnitInfo


class Formatter(Protocol):
    def format_zero_or_one(self, value: int | float) -> str:
        ...

    def format_small_number(self, value: int | float) -> str:
        ...

    def format_large_number(self, value: int | float) -> str:
        ...


def _apply_precision(
    value: int | float, precision: metrics.AutoPrecision | metrics.StrictPrecision
) -> float:
    value_floor = math.floor(value)
    if value == value_floor:
        return value
    fractional_part = value - value_floor
    digits = precision.digits
    if isinstance(precision, metrics.AutoPrecision):
        if exponent := abs(math.ceil(math.log(fractional_part, 10))):
            digits = max(exponent + 1, precision.digits)
    return value_floor + round(fractional_part, digits)


def _sanitize(value: str) -> str:
    return value.rstrip("0").rstrip(".") if "." in value else value


@dataclass(frozen=True)
class Preformatted:
    value: int | float
    suffix: str


class NotationFormatter:
    def __init__(
        self,
        symbol: str,
        precision: metrics.AutoPrecision | metrics.StrictPrecision,
        preformat_small_number: Callable[[int | float, str], Preformatted],
        preformat_large_number: Callable[[int | float, str], Preformatted],
    ) -> None:
        self.symbol: Final = symbol
        self.precision: Final = precision
        self.preformat_small_number: Final = preformat_small_number
        self.preformat_large_number: Final = preformat_large_number

    def format_zero_or_one(self, value: int | float) -> str:
        return f"{value} {self.symbol}"

    def format_small_number(self, value: int | float) -> str:
        preformatted = self.preformat_small_number(value, self.symbol)
        value_with_precision = _apply_precision(preformatted.value, self.precision)
        return f"{_sanitize(str(value_with_precision))}{preformatted.suffix}"

    def format_large_number(self, value: int | float) -> str:
        preformatted = self.preformat_large_number(value, self.symbol)
        value_with_precision = _apply_precision(preformatted.value, self.precision)
        return f"{_sanitize(str(value_with_precision))}{preformatted.suffix}"


def _preformat_number(value: int | float, symbol: str) -> Preformatted:
    return Preformatted(value, f" {symbol}")


def _si_preformat_small_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10)) - 1
    if exponent <= -24:
        factor = pow(1000, 8)
        prefix = "y"
    elif exponent <= -21:
        factor = pow(1000, 7)
        prefix = "z"
    elif exponent <= -18:
        factor = pow(1000, 6)
        prefix = "a"
    elif exponent <= -15:
        factor = pow(1000, 5)
        prefix = "f"
    elif exponent <= -12:
        factor = pow(1000, 4)
        prefix = "p"
    elif exponent <= -9:
        factor = pow(1000, 3)
        prefix = "n"
    elif exponent <= -6:
        factor = pow(1000, 2)
        prefix = "μ"
    elif exponent <= -3:
        factor = 1000
        prefix = "m"
    else:
        factor = 1
        prefix = ""
    return Preformatted(value * factor, f" {prefix}{symbol}")


def _si_preformat_large_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10))
    if exponent >= 24:
        factor = pow(1000, 8)
        prefix = "Y"
    elif exponent >= 21:
        factor = pow(1000, 7)
        prefix = "Z"
    elif exponent >= 18:
        factor = pow(1000, 6)
        prefix = "E"
    elif exponent >= 15:
        factor = pow(1000, 5)
        prefix = "P"
    elif exponent >= 12:
        factor = pow(1000, 4)
        prefix = "T"
    elif exponent >= 9:
        factor = pow(1000, 3)
        prefix = "G"
    elif exponent >= 6:
        factor = pow(1000, 2)
        prefix = "M"
    elif exponent >= 3:
        factor = 1000
        prefix = "k"
    else:
        factor = 1
        prefix = ""
    return Preformatted(value / factor, f" {prefix}{symbol}")


def _iec_preformat_large_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 2))
    if exponent >= 80:
        factor = pow(1024, 8)
        prefix = "Yi"
    elif exponent >= 70:
        factor = pow(1024, 7)
        prefix = "Zi"
    elif exponent >= 60:
        factor = pow(1024, 6)
        prefix = "Ei"
    elif exponent >= 50:
        factor = pow(1024, 5)
        prefix = "Pi"
    elif exponent >= 40:
        factor = pow(1024, 4)
        prefix = "Ti"
    elif exponent >= 30:
        factor = pow(1024, 3)
        prefix = "Gi"
    elif exponent >= 20:
        factor = pow(1024, 2)
        prefix = "Mi"
    elif exponent >= 10:
        factor = 1024
        prefix = "Ki"
    else:
        factor = 1
        prefix = ""
    return Preformatted(value / factor, f" {prefix}{symbol}")


def _standard_scientific_preformat_small_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10))
    return Preformatted(value / pow(10, exponent), f"e{exponent} {symbol}")


def _standard_scientific_preformat_large_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10))
    return Preformatted(value / pow(10, exponent), f"e+{exponent} {symbol}")


def _engineering_scientific_preformat_small_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10) / 3) * 3
    return Preformatted(value / pow(10, exponent), f"e{exponent} {symbol}")


def _engineering_scientific_preformat_large_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(10000, 10) / 3) * 3
    return Preformatted(value / pow(10, exponent), f"e+{exponent} {symbol}")


def _time_preformat_small_number(value: int | float, symbol: str) -> Preformatted:
    exponent = math.floor(math.log(value, 10)) - 1
    if exponent <= -6:
        factor = pow(1000, 2)
        symbol = "µs"
    elif exponent <= -3:
        factor = 1000
        symbol = "ms"
    else:
        factor = 1
        symbol = "s"
    return Preformatted(value * factor, f" {symbol}")


_ONE_DAY: Final = 86400
_ONE_HOUR: Final = 3600
_ONE_MINUTE: Final = 60


def _time_preformat_large_number(value: int | float, symbol: str) -> Preformatted:
    if value >= _ONE_DAY:
        factor = _ONE_DAY
        symbol = "d"
    elif value >= _ONE_HOUR:
        factor = _ONE_HOUR
        symbol = "h"
    elif value >= _ONE_MINUTE:
        factor = _ONE_MINUTE
        symbol = "min"
    else:
        factor = 1
        symbol = "s"
    return Preformatted(value / factor, f" {symbol}")


def _render(value: int | float, formatter: Formatter) -> str:
    if value < 0:
        return f"-{_render(abs(value), formatter)}"
    if value in (0, 1):
        return formatter.format_zero_or_one(value).strip()
    if value < 1:
        return formatter.format_small_number(value).strip()
    # value > 1
    return formatter.format_large_number(value).strip()


def parse_or_add_unit(unit: metrics.Unit) -> UnitInfo:
    if (
        unit_id := (
            f"{unit.notation.__class__.__name__}_{unit.notation.symbol}"
            f"_{unit.precision.__class__.__name__}_{unit.precision.digits}"
        )
    ) in units_from_api:
        return units_from_api[unit_id]

    match unit.notation:
        case metrics.DecimalNotation():
            preformat_small_number = _preformat_number
            preformat_large_number = _preformat_number
            js_preformat_small_number = "preformat_number"
            js_preformat_large_number = "preformat_number"
        case metrics.SINotation():
            preformat_small_number = _si_preformat_small_number
            preformat_large_number = _si_preformat_large_number
            js_preformat_small_number = "si_preformat_small_number"
            js_preformat_large_number = "si_preformat_large_number"
        case metrics.IECNotation():
            preformat_small_number = _preformat_number
            preformat_large_number = _iec_preformat_large_number
            js_preformat_small_number = "preformat_number"
            js_preformat_large_number = "iec_preformat_large_number"
        case metrics.StandardScientificNotation():
            preformat_small_number = _standard_scientific_preformat_small_number
            preformat_large_number = _standard_scientific_preformat_large_number
            js_preformat_small_number = "standard_scientific_preformat_small_number"
            js_preformat_large_number = "standard_scientific_preformat_large_number"
        case metrics.EngineeringScientificNotation():
            preformat_small_number = _engineering_scientific_preformat_small_number
            preformat_large_number = _engineering_scientific_preformat_large_number
            js_preformat_small_number = "engineering_scientific_preformat_small_number"
            js_preformat_large_number = "engineering_scientific_preformat_large_number"
        case metrics.TimeNotation():
            preformat_small_number = _time_preformat_small_number
            preformat_large_number = _time_preformat_large_number
            js_preformat_small_number = "time_preformat_small_number"
            js_preformat_large_number = "time_preformat_large_number"

    return units_from_api.register(
        UnitInfo(
            id=unit_id,
            title=unit.notation.symbol,
            symbol=unit.notation.symbol,
            render=lambda v: _render(
                v,
                NotationFormatter(
                    unit.notation.symbol,
                    unit.precision,
                    preformat_small_number,
                    preformat_large_number,
                ),
            ),
            js_render=f"""v => cmk.number_format.render(
    v,
    new cmk.number_format.NotationFormatter(
        "{unit.notation.symbol}",
        new cmk.number_format.{unit.precision.__class__.__name__}({unit.precision.digits}),
        cmk.number_format.{js_preformat_small_number},
        cmk.number_format.{js_preformat_large_number},
    )
)""",
        )
    )


@dataclass(frozen=True)
class RGB:
    red: int
    green: int
    blue: int


def color_to_rgb(color: metrics.Color) -> RGB:
    match color:
        case metrics.Color.LIGHT_RED:
            return RGB(255, 51, 51)
        case metrics.Color.RED:
            return RGB(204, 0, 0)
        case metrics.Color.DARK_RED:
            return RGB(122, 0, 0)

        case metrics.Color.LIGHT_ORANGE:
            return RGB(255, 163, 71)
        case metrics.Color.ORANGE:
            return RGB(255, 127, 0)
        case metrics.Color.DARK_ORANGE:
            return RGB(204, 102, 0)

        case metrics.Color.LIGHT_YELLOW:
            return RGB(255, 255, 112)
        case metrics.Color.YELLOW:
            return RGB(245, 245, 0)
        case metrics.Color.DARK_YELLOW:
            return RGB(204, 204, 0)

        case metrics.Color.LIGHT_GREEN:
            return RGB(112, 255, 112)
        case metrics.Color.GREEN:
            return RGB(0, 255, 0)
        case metrics.Color.DARK_GREEN:
            return RGB(0, 143, 0)

        case metrics.Color.LIGHT_BLUE:
            return RGB(71, 71, 255)
        case metrics.Color.BLUE:
            return RGB(0, 0, 255)
        case metrics.Color.DARK_BLUE:
            return RGB(0, 0, 163)

        case metrics.Color.LIGHT_CYAN:
            return RGB(153, 255, 255)
        case metrics.Color.CYAN:
            return RGB(0, 255, 255)
        case metrics.Color.DARK_CYAN:
            return RGB(0, 184, 184)

        case metrics.Color.LIGHT_PURPLE:
            return RGB(163, 71, 255)
        case metrics.Color.PURPLE:
            return RGB(127, 0, 255)
        case metrics.Color.DARK_PURPLE:
            return RGB(82, 0, 163)

        case metrics.Color.LIGHT_PINK:
            return RGB(255, 214, 220)
        case metrics.Color.PINK:
            return RGB(255, 192, 203)
        case metrics.Color.DARK_PINK:
            return RGB(255, 153, 170)

        case metrics.Color.LIGHT_BROWN:
            return RGB(184, 92, 0)
        case metrics.Color.BROWN:
            return RGB(143, 71, 0)
        case metrics.Color.DARK_BROWN:
            return RGB(102, 51, 0)

        case metrics.Color.LIGHT_GRAY:
            return RGB(153, 153, 153)
        case metrics.Color.GRAY:
            return RGB(127, 127, 127)
        case metrics.Color.DARK_GRAY:
            return RGB(92, 92, 92)

        case metrics.Color.BLACK:
            return RGB(0, 0, 0)
        case metrics.Color.WHITE:
            return RGB(255, 255, 255)


def parse_color(color: metrics.Color) -> str:
    rgb = color_to_rgb(color)
    return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
