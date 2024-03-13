#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from cmk.graphing.v1 import metrics

from ._loader import units_from_api
from ._type_defs import UnitInfo

_MAX_DIGITS: Final = 5


@dataclass(frozen=True)
class Suffix:
    prefix: str
    symbol: str

    def use_prefix(self, prefix: str) -> bool:
        if self.prefix and prefix:
            return self.prefix == prefix
        return True

    def use_symbol(self, symbol: str) -> bool:
        if self.symbol and symbol:
            return self.symbol == symbol
        return True


@dataclass(frozen=True)
class Formatted:
    value: int | float
    suffix: Suffix

    def format_value(self) -> str:
        value_ = str(self.value)
        return value_.rstrip("0").rstrip(".") if "." in value_ else value_


@dataclass(frozen=True)
class NumLabelRange:
    left: int
    right: int


@dataclass(frozen=True)
class Label:
    position: int | float
    text: str


@dataclass(frozen=True)
class NotationFormatter:
    symbol: str
    precision: metrics.AutoPrecision | metrics.StrictPrecision

    @abc.abstractmethod
    def ident(
        self,
    ) -> Literal["Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        raise NotImplementedError()

    @abc.abstractmethod
    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        raise NotImplementedError()

    def _apply_precision(self, value: int | float) -> float:
        value_floor = math.floor(value)
        if value == value_floor:
            return value
        digits = self.precision.digits
        if isinstance(self.precision, metrics.AutoPrecision):
            if exponent := abs(math.ceil(math.log(value - value_floor, 10))):
                digits = max(exponent + 1, self.precision.digits)
        return round(value, min(digits, _MAX_DIGITS))

    def _format(self, value: int | float, suffix: Suffix) -> Formatted:
        if value < 0:
            formatted = self._format(abs(value), suffix)
            return Formatted(-formatted.value, formatted.suffix)
        if value in (0, 1):
            return Formatted(value, Suffix("", self.symbol))
        if value < 1:
            formatted = self._preformat_small_number(value, suffix)
        else:  # value > 1
            formatted = self._preformat_large_number(value, suffix)
        return Formatted(self._apply_precision(formatted.value), formatted.suffix)

    @abc.abstractmethod
    def _format_suffix(self, suffix: Suffix) -> str:
        raise NotImplementedError()

    def render(self, value: int | float) -> str:
        formatted = self._format(value, Suffix("", ""))
        return f"{formatted.format_value()}{self._format_suffix(formatted.suffix)}".strip()

    @abc.abstractmethod
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        raise NotImplementedError()

    def render_y_labels(
        self, max_y: int | float, num_label_range: NumLabelRange
    ) -> Sequence[Label]:
        assert max_y >= 0
        if max_y == 0:
            return []

        if max_y < 1:
            atoms = self._compute_small_y_label_atoms(max_y)
        else:  # max_y >= 1
            max_y = math.ceil(max_y)
            atoms = self._compute_large_y_label_atoms(max_y)

        if possible_atoms := [
            (a, int(q))
            for a in atoms
            if num_label_range.left <= (q := max_y // a) <= num_label_range.right
        ]:
            # Take the entry with the smallest amount of labels.
            atom, quotient = min(possible_atoms, key=lambda t: t[1])
        else:
            atom = max_y / num_label_range.right
            quotient = int(max_y / atom)

        first = self._format(atom, Suffix("", ""))
        return [
            Label(
                atom * i,
                f"{formatted.format_value()}{self._format_suffix(formatted.suffix)}".strip(),
            )
            for i in range(1, quotient + 1)
            for formatted in (self._format(atom * i, first.suffix),)
        ]


_BASIC_DECIMAL_ATOMS: Final = [1, 2, 5, 10, 20, 50]


class DecimalFormatter(NotationFormatter):
    def ident(self) -> Literal["Decimal"]:
        return "Decimal"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        return Formatted(value, Suffix("", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        return Formatted(value, Suffix("", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f" {suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class SIFormatter(NotationFormatter):
    def ident(self) -> Literal["SI"]:
        return "SI"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 10)) - 1
        for exp, power, prefix in (
            (-24, 8, "y"),
            (-21, 7, "z"),
            (-18, 6, "a"),
            (-15, 5, "f"),
            (-12, 4, "p"),
            (-9, 3, "n"),
            (-6, 2, "μ"),
            (-3, 1, "m"),
        ):
            if exponent <= exp and suffix.use_prefix(prefix):
                return Formatted(value * pow(1000, power), Suffix(prefix, self.symbol))
        return Formatted(value, Suffix("", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(round(math.log(value, 10)))
        for exp, power, prefix in (
            (24, 8, "Y"),
            (21, 7, "Z"),
            (18, 6, "E"),
            (15, 5, "P"),
            (12, 4, "T"),
            (9, 3, "G"),
            (6, 2, "M"),
            (3, 1, "k"),
        ):
            if exponent >= exp and suffix.use_prefix(prefix):
                return Formatted(value / pow(1000, power), Suffix(prefix, self.symbol))
        return Formatted(value, Suffix("", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f" {suffix.prefix}{suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class IECFormatter(NotationFormatter):
    def ident(self) -> Literal["IEC"]:
        return "IEC"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        return Formatted(value, Suffix("", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 2))
        for exp, power, prefix in (
            (80, 8, "Yi"),
            (70, 7, "Zi"),
            (60, 6, "Ei"),
            (50, 5, "Pi"),
            (40, 4, "Ti"),
            (30, 3, "Gi"),
            (20, 2, "Mi"),
            (10, 1, "Ki"),
        ):
            if exponent >= exp and suffix.use_prefix(prefix):
                return Formatted(value / pow(1024, power), Suffix(prefix, self.symbol))
        return Formatted(value, Suffix("", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f" {suffix.prefix}{suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        exponent = math.floor(math.log(max_y, 2))
        return [pow(2, e) for e in range(1, exponent + 1)]


class StandardScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["StandardScientific"]:
        return "StandardScientific"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 10))
        return Formatted(value / pow(10, exponent), Suffix(f"e{exponent}", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 10))
        return Formatted(value / pow(10, exponent), Suffix(f"e+{exponent}", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f"{suffix.prefix} {suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class EngineeringScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["EngineeringScientific"]:
        return "EngineeringScientific"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 10) / 3) * 3
        return Formatted(value / pow(10, exponent), Suffix(f"e{exponent}", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(round(math.log(value, 10)) // 3) * 3
        return Formatted(value / pow(10, exponent), Suffix(f"e+{exponent}", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f"{suffix.prefix} {suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


_ONE_DAY: Final = 86400
_ONE_HOUR: Final = 3600
_ONE_MINUTE: Final = 60
_BASIC_TIME_ATOMS: Final = [
    1,
    2,
    5,
    10,
    20,
    30,
    _ONE_MINUTE,
    2 * _ONE_MINUTE,
    5 * _ONE_MINUTE,
    10 * _ONE_MINUTE,
    20 * _ONE_MINUTE,
    30 * _ONE_MINUTE,
    _ONE_HOUR,
    2 * _ONE_HOUR,
    4 * _ONE_HOUR,
    6 * _ONE_HOUR,
    8 * _ONE_HOUR,
    12 * _ONE_HOUR,
    _ONE_DAY,
    2 * _ONE_DAY,
    5 * _ONE_DAY,
    10 * _ONE_DAY,
    20 * _ONE_DAY,
    50 * _ONE_DAY,
    100 * _ONE_DAY,
]


class TimeFormatter(NotationFormatter):
    def ident(self) -> Literal["Time"]:
        return "Time"

    def _preformat_small_number(self, value: int | float, suffix: Suffix) -> Formatted:
        exponent = math.floor(math.log(value, 10)) - 1
        for exp, power, prefix in (
            (-6, 2, "μ"),
            (-3, 1, "m"),
        ):
            if exponent <= exp and suffix.use_prefix(prefix):
                return Formatted(value * pow(1000, power), Suffix(prefix, self.symbol))
        return Formatted(value, Suffix("", self.symbol))

    def _preformat_large_number(self, value: int | float, suffix: Suffix) -> Formatted:
        for factor, symbol in (
            (_ONE_DAY, "d"),
            (_ONE_HOUR, "h"),
            (_ONE_MINUTE, "min"),
        ):
            if value >= factor and suffix.use_symbol(symbol):
                return Formatted(value / factor, Suffix("", symbol))
        return Formatted(value, Suffix("", self.symbol))

    def _format_suffix(self, suffix: Suffix) -> str:
        return f" {suffix.prefix}{suffix.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log(max_y, 10)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        if max_y >= _ONE_DAY:
            return (
                _BASIC_TIME_ATOMS[15:19] if int(max_y // _ONE_DAY) < 2 else _BASIC_TIME_ATOMS[15:]
            )
        if max_y >= _ONE_HOUR:
            return _BASIC_TIME_ATOMS[9:18]
        if max_y >= _ONE_MINUTE:
            return _BASIC_TIME_ATOMS[3:12]
        return _BASIC_DECIMAL_ATOMS[:6]


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

    match unit.precision:
        case metrics.AutoPrecision():
            precision_title = f"auto precision {unit.precision.digits}"
        case metrics.StrictPrecision():
            precision_title = f"strict precision {unit.precision.digits}"
    title_parts = [
        unit.notation.symbol or "no symbol",
        f"({formatter.ident()}, {precision_title})",
    ]
    return units_from_api.register(
        UnitInfo(
            id=unit_id,
            title=" ".join(title_parts),
            symbol=unit.notation.symbol,
            render=formatter.render,
            js_render=f"""v => new cmk.number_format.{js_formatter}(
    "{unit.notation.symbol}",
    new cmk.number_format.{unit.precision.__class__.__name__}({unit.precision.digits}),
).render(v)""",
            formatter_ident=formatter.ident(),
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
