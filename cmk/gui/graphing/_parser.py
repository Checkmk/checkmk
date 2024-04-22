#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from cmk.gui.valuespec import Age, Float, Integer, Percentage

from cmk.graphing.v1 import metrics

from ._loader import units_from_api
from ._type_defs import UnitInfo

_MAX_DIGITS: Final = 5


@dataclass(frozen=True)
class Preformatted:
    value: int | float
    prefix: str
    symbol: str


@dataclass(frozen=True)
class Formatted:
    text: str
    prefix: str
    symbol: str


def _find_prefix_power(use_prefix: str, prefixes: Sequence[tuple[int, int, str]]) -> int:
    for _exp, power, prefix in prefixes:
        if use_prefix == prefix:
            return power
    return 1


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
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        raise NotImplementedError()

    def _apply_precision(
        self, value: int | float, compute_auto_precision_digits: Callable[[int, int], int]
    ) -> float:
        value_floor = math.floor(value)
        if value == value_floor:
            return value
        digits = self.precision.digits
        if isinstance(self.precision, metrics.AutoPrecision):
            if exponent := abs(math.ceil(math.log10(value - value_floor))):
                digits = compute_auto_precision_digits(exponent, self.precision.digits)
        return round(value, min(digits, _MAX_DIGITS))

    def _preformat(
        self, value: int | float, *, use_prefix: str = "", use_symbol: str = ""
    ) -> Sequence[Preformatted]:
        assert value >= 0
        if value in (0, 1):
            return [Preformatted(value, "", self.symbol)]
        if value < 1:
            return self._preformat_small_number(value, use_prefix, use_symbol)
        # value > 1
        return self._preformat_large_number(value, use_prefix, use_symbol)

    @abc.abstractmethod
    def _compose(self, formatted: Formatted) -> str:
        raise NotImplementedError()

    def _postformat(
        self,
        formatted_parts: Sequence[Preformatted],
        compute_auto_precision_digits: Callable[[int, int], int],
    ) -> str:
        results = []
        for formatted in formatted_parts:
            text = str(self._apply_precision(formatted.value, compute_auto_precision_digits))
            results.append(
                self._compose(
                    Formatted(
                        text.rstrip("0").rstrip(".") if "." in text else text,
                        formatted.prefix,
                        formatted.symbol,
                    )
                ).strip()
            )
        return " ".join(results)

    def render(self, value: int | float) -> str:
        sign = "" if value >= 0 else "-"
        postformatted = self._postformat(
            self._preformat(abs(value)),
            lambda exponent, digits: max(exponent + 1, digits),
        )
        return f"{sign}{postformatted}"

    @abc.abstractmethod
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        raise NotImplementedError()

    def render_y_labels(self, max_y: int | float, mean_num_labels: float) -> Sequence[Label]:
        assert max_y >= 0
        assert mean_num_labels >= 0
        if max_y == 0 or mean_num_labels == 0:
            return []

        if max_y < 1:
            atoms = self._compute_small_y_label_atoms(max_y)
        else:  # max_y >= 1
            atoms = self._compute_large_y_label_atoms(max_y)

        if possible_atoms := [(a, q) for a in atoms if (q := int(max_y // a))]:
            atom, quotient = min(possible_atoms, key=lambda t: abs(t[1] - mean_num_labels))
        else:
            atom = int(max_y / mean_num_labels)
            quotient = int(max_y // atom)

        first = self._preformat(atom)[0]
        return [
            Label(
                atom * i,
                self._postformat(
                    self._preformat(atom * i, use_prefix=first.prefix, use_symbol=first.symbol),
                    lambda exponent, digits: exponent + digits,
                ),
            )
            for i in range(1, quotient + 1)
        ]


_BASIC_DECIMAL_ATOMS: Final = [1, 2, 5, 10, 20, 50]


class DecimalFormatter(NotationFormatter):
    def ident(self) -> Literal["Decimal"]:
        return "Decimal"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        return [Preformatted(value, "", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        return [Preformatted(value, "", self.symbol)]

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text} {formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


_SI_SMALL_PREFIXES: Final = [
    (-24, 8, "y"),
    (-21, 7, "z"),
    (-18, 6, "a"),
    (-15, 5, "f"),
    (-12, 4, "p"),
    (-9, 3, "n"),
    (-6, 2, "μ"),
    (-3, 1, "m"),
]
_SI_LARGE_PREFIXES: Final = [
    (24, 8, "Y"),
    (21, 7, "Z"),
    (18, 6, "E"),
    (15, 5, "P"),
    (12, 4, "T"),
    (9, 3, "G"),
    (6, 2, "M"),
    (3, 1, "k"),
]


class SIFormatter(NotationFormatter):
    def ident(self) -> Literal["SI"]:
        return "SI"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _SI_SMALL_PREFIXES)
            return [Preformatted(value * pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value)) - 1
        for exp, power, prefix in _SI_SMALL_PREFIXES:
            if exponent <= exp:
                return [Preformatted(value * pow(1000, power), prefix, self.symbol)]
        return [Preformatted(value, "", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _SI_LARGE_PREFIXES)
            return [Preformatted(value / pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value))
        for exp, power, prefix in _SI_LARGE_PREFIXES:
            if exponent >= exp:
                return [Preformatted(value / pow(1000, power), prefix, self.symbol)]
        return [Preformatted(value, "", self.symbol)]

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text} {formatted.prefix}{formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


_IEC_LARGE_PREFIXES: Final = [
    (80, 8, "Yi"),
    (70, 7, "Zi"),
    (60, 6, "Ei"),
    (50, 5, "Pi"),
    (40, 4, "Ti"),
    (30, 3, "Gi"),
    (20, 2, "Mi"),
    (10, 1, "Ki"),
]


class IECFormatter(NotationFormatter):
    def ident(self) -> Literal["IEC"]:
        return "IEC"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        return [Preformatted(value, "", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _IEC_LARGE_PREFIXES)
            return [Preformatted(value / pow(1024, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log2(value))
        for exp, power, prefix in _IEC_LARGE_PREFIXES:
            if exponent >= exp:
                return [Preformatted(value / pow(1024, power), prefix, self.symbol)]
        return [Preformatted(value, "", self.symbol)]

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text} {formatted.prefix}{formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        exponent = math.floor(math.log2(max_y))
        return [pow(2, e) for e in range(exponent + 1)]


class StandardScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["StandardScientific"]:
        return "StandardScientific"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        exponent = math.floor(math.log10(value))
        return [Preformatted(value / pow(10, exponent), f"e{exponent}", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        exponent = math.floor(math.log10(value))
        return [Preformatted(value / pow(10, exponent), f"e+{exponent}", self.symbol)]

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text}{formatted.prefix} {formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class EngineeringScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["EngineeringScientific"]:
        return "EngineeringScientific"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        exponent = math.floor(math.log10(value) / 3) * 3
        return [Preformatted(value / pow(10, exponent), f"e{exponent}", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        exponent = math.floor(math.log10(value) // 3) * 3
        return [Preformatted(value / pow(10, exponent), f"e+{exponent}", self.symbol)]

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text}{formatted.prefix} {formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
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
_TIME_SMALL_PREFIXES: Final = [
    (-6, 2, "μ"),
    (-3, 1, "m"),
]
_TIME_LARGE_SYMBOLS: Final = [
    (_ONE_DAY, "d"),
    (_ONE_HOUR, "h"),
    (_ONE_MINUTE, "min"),
]


class TimeFormatter(NotationFormatter):
    def ident(self) -> Literal["Time"]:
        return "Time"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _TIME_SMALL_PREFIXES)
            return [Preformatted(value * pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value)) - 1
        for exp, power, prefix in _TIME_SMALL_PREFIXES:
            if exponent <= exp:
                return [Preformatted(value * pow(1000, power), prefix, self.symbol)]
        return [Preformatted(value, "", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        if not use_symbol:
            for factor, symbol in _TIME_LARGE_SYMBOLS:
                if value >= factor:
                    use_symbol = symbol
                    break
        rounded_value = round(value)
        formatted_parts = []
        match use_symbol:
            case "d":
                days = int(rounded_value // _ONE_DAY)
                formatted_parts.append(Preformatted(days, "", "d"))
                if days < 10 and (hours := round((rounded_value - days * _ONE_DAY) / _ONE_HOUR)):
                    formatted_parts.append(Preformatted(hours, "", "h"))
            case "h":
                hours = int(rounded_value // _ONE_HOUR)
                formatted_parts.append(Preformatted(hours, "", "h"))
                if minutes := round((rounded_value - hours * _ONE_HOUR) / _ONE_MINUTE):
                    formatted_parts.append(Preformatted(minutes, "", "min"))
            case "min":
                minutes = int(rounded_value // _ONE_MINUTE)
                formatted_parts.append(Preformatted(minutes, "", "min"))
                if seconds := round(rounded_value - minutes * _ONE_MINUTE):
                    formatted_parts.append(Preformatted(seconds, "", "s"))
            case _:
                formatted_parts.append(Preformatted(value, "", "s"))
        return formatted_parts

    def _compose(self, formatted: Formatted) -> str:
        return f"{formatted.text} {formatted.prefix}{formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        if max_y >= _ONE_DAY:
            if (q := int(max_y // _ONE_DAY)) < 2:
                return _BASIC_TIME_ATOMS[15:]
            exponent = math.floor(math.log10(q))
            return _BASIC_TIME_ATOMS[15:] + [
                _ONE_DAY * a * pow(10, exponent - 1) for a in _BASIC_DECIMAL_ATOMS
            ]
        if max_y >= _ONE_HOUR:
            return _BASIC_TIME_ATOMS[9:18]
        if max_y >= _ONE_MINUTE:
            return _BASIC_TIME_ATOMS[3:12]
        return _BASIC_DECIMAL_ATOMS[:6]


def _vs_type(unit: metrics.Unit) -> type[Age] | type[Float] | type[Integer] | type[Percentage]:
    if isinstance(unit.notation, metrics.TimeNotation):
        return Age
    if unit.notation.symbol.startswith("%"):
        return Percentage
    if unit.precision.digits == 0:
        return Integer
    return Float


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
            valuespec=_vs_type(unit),
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
            return RGB(255, 112, 112)
        case metrics.Color.RED:
            return RGB(255, 41, 41)
        case metrics.Color.DARK_RED:
            return RGB(164, 0, 0)

        case metrics.Color.LIGHT_ORANGE:
            return RGB(255, 150, 100)
        case metrics.Color.ORANGE:
            return RGB(255, 110, 33)
        case metrics.Color.DARK_ORANGE:
            return RGB(180, 70, 10)

        case metrics.Color.LIGHT_YELLOW:
            return RGB(255, 255, 120)
        case metrics.Color.YELLOW:
            return RGB(245, 245, 50)
        case metrics.Color.DARK_YELLOW:
            return RGB(170, 170, 0)

        case metrics.Color.LIGHT_GREEN:
            return RGB(165, 255, 85)
        case metrics.Color.GREEN:
            return RGB(55, 250, 55)
        case metrics.Color.DARK_GREEN:
            return RGB(40, 140, 15)

        case metrics.Color.LIGHT_BLUE:
            return RGB(135, 206, 250)
        case metrics.Color.BLUE:
            return RGB(30, 144, 255)
        case metrics.Color.DARK_BLUE:
            return RGB(30, 30, 200)

        case metrics.Color.LIGHT_CYAN:
            return RGB(150, 255, 255)
        case metrics.Color.CYAN:
            return RGB(30, 230, 230)
        case metrics.Color.DARK_CYAN:
            return RGB(20, 135, 140)

        case metrics.Color.LIGHT_PURPLE:
            return RGB(220, 160, 255)
        case metrics.Color.PURPLE:
            return RGB(180, 65, 240)
        case metrics.Color.DARK_PURPLE:
            return RGB(120, 20, 160)

        case metrics.Color.LIGHT_PINK:
            return RGB(255, 160, 240)
        case metrics.Color.PINK:
            return RGB(255, 100, 255)
        case metrics.Color.DARK_PINK:
            return RGB(210, 20, 190)

        case metrics.Color.LIGHT_BROWN:
            return RGB(230, 180, 140)
        case metrics.Color.BROWN:
            return RGB(191, 133, 72)
        case metrics.Color.DARK_BROWN:
            return RGB(124, 62, 4)

        case metrics.Color.LIGHT_GRAY:
            return RGB(200, 200, 200)
        case metrics.Color.GRAY:
            return RGB(164, 164, 164)
        case metrics.Color.DARK_GRAY:
            return RGB(121, 121, 121)

        case metrics.Color.BLACK:
            return RGB(0, 0, 0)
        case metrics.Color.WHITE:
            return RGB(255, 255, 255)


def parse_color(color: metrics.Color) -> str:
    rgb = color_to_rgb(color)
    return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
