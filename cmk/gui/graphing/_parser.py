#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from dataclasses import dataclass
from typing import Final

from cmk.graphing.v1 import metrics

from ._loader import units_from_api
from ._type_defs import UnitInfo

_MAX_DIGITS: Final = 5


@dataclass(frozen=True)
class Preformatted:
    value: int | float
    suffix: str


def _sanitize(value: str) -> str:
    return value.rstrip("0").rstrip(".") if "." in value else value


@dataclass(frozen=True)
class NotationFormatter:
    symbol: str
    precision: metrics.AutoPrecision | metrics.StrictPrecision

    @abc.abstractmethod
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        raise NotImplementedError()

    @abc.abstractmethod
    def _preformat_large_number(self, value: int | float) -> Preformatted:
        raise NotImplementedError()

    def _apply_precision(self, value: int | float) -> float:
        value_floor = math.floor(value)
        if value == value_floor:
            return value
        fractional_part = value - value_floor
        digits = self.precision.digits
        if isinstance(self.precision, metrics.AutoPrecision):
            if exponent := abs(math.ceil(math.log(fractional_part, 10))):
                digits = max(exponent + 1, self.precision.digits)
        return value_floor + round(fractional_part, min(digits, _MAX_DIGITS))

    def render(self, value: int | float) -> str:
        if value < 0:
            return f"-{self.render(abs(value))}"
        if value in (0, 1):
            return f"{_sanitize(str(value))} {self.symbol}".strip()
        if value < 1:
            preformatted = self._preformat_small_number(value)
        else:  # value > 1
            preformatted = self._preformat_large_number(value)
        value_with_precision = self._apply_precision(preformatted.value)
        return f"{_sanitize(str(value_with_precision))}{preformatted.suffix}".strip()


class DecimalFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        return Preformatted(value, f" {self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
        return Preformatted(value, f" {self.symbol}")


class SIFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
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
        return Preformatted(value * factor, f" {prefix}{self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
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
        return Preformatted(value / factor, f" {prefix}{self.symbol}")


class IECFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        return Preformatted(value, f" {self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
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
        return Preformatted(value / factor, f" {prefix}{self.symbol}")


class StandardScientificFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        exponent = math.floor(math.log(value, 10))
        return Preformatted(value / pow(10, exponent), f"e{exponent} {self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
        exponent = math.floor(math.log(value, 10))
        return Preformatted(value / pow(10, exponent), f"e+{exponent} {self.symbol}")


class EngineeringScientificFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        exponent = math.floor(math.log(value, 10) / 3) * 3
        return Preformatted(value / pow(10, exponent), f"e{exponent} {self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
        exponent = math.floor(round(math.log(value, 10)) // 3) * 3
        return Preformatted(value / pow(10, exponent), f"e+{exponent} {self.symbol}")


_ONE_DAY: Final = 86400
_ONE_HOUR: Final = 3600
_ONE_MINUTE: Final = 60


class TimeFormatter(NotationFormatter):
    def _preformat_small_number(self, value: int | float) -> Preformatted:
        exponent = math.floor(math.log(value, 10)) - 1
        if exponent <= -6:
            factor = pow(1000, 2)
            prefix = "µ"
        elif exponent <= -3:
            factor = 1000
            prefix = "m"
        else:
            factor = 1
            prefix = ""
        return Preformatted(value * factor, f" {prefix}{self.symbol}")

    def _preformat_large_number(self, value: int | float) -> Preformatted:
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
            symbol = self.symbol
        return Preformatted(value / factor, f" {symbol}")


def parse_or_add_unit(unit: metrics.Unit) -> UnitInfo:
    if (
        unit_id := (
            f"{unit.notation.__class__.__name__}_{unit.notation.symbol}"
            f"_{unit.precision.__class__.__name__}_{unit.precision.digits}"
        )
    ) in units_from_api:
        return units_from_api[unit_id]

    formatter: NotationFormatter
    match unit.notation:
        case metrics.DecimalNotation():
            formatter = DecimalFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "DecimalFormatter"
        case metrics.SINotation():
            formatter = SIFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "SIFormatter"
        case metrics.IECNotation():
            formatter = IECFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "IECFormatter"
        case metrics.StandardScientificNotation():
            formatter = StandardScientificFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "StandardScientificFormatter"
        case metrics.EngineeringScientificNotation():
            formatter = EngineeringScientificFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "EngineeringScientificFormatter"
        case metrics.TimeNotation():
            formatter = TimeFormatter(unit.notation.symbol, unit.precision)
            js_formatter = "TimeFormatter"

    return units_from_api.register(
        UnitInfo(
            id=unit_id,
            title=unit.notation.symbol,
            symbol=unit.notation.symbol,
            render=formatter.render,
            js_render=f"""v => new cmk.number_format.{js_formatter}(
    "{unit.notation.symbol}",
    new cmk.number_format.{unit.precision.__class__.__name__}({unit.precision.digits}),
).render(v)""",
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
