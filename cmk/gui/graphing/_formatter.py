#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from pydantic import BaseModel

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


class AutoPrecision(BaseModel, frozen=True):
    type: Literal["auto"] = "auto"
    digits: int


class StrictPrecision(BaseModel, frozen=True):
    type: Literal["strict"] = "strict"
    digits: int


@dataclass(frozen=True)
class NotationFormatter:
    symbol: str
    precision: AutoPrecision | StrictPrecision
    use_max_digits_for_labels: bool = True

    @abc.abstractmethod
    def ident(
        self,
    ) -> Literal["Decimal", "SI", "IEC", "StandardScientific", "EngineeringScientific", "Time"]: ...

    @property
    @abc.abstractmethod
    def js_formatter_name(self) -> str: ...

    @abc.abstractmethod
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]: ...

    @abc.abstractmethod
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]: ...

    def _apply_precision(
        self,
        value: int | float,
        compute_auto_precision_digits: Callable[[int, int], int],
        use_max_digits_for_labels: bool,
    ) -> float:
        value_floor = math.floor(value)
        if value == value_floor:
            return value
        digits = self.precision.digits
        if isinstance(self.precision, AutoPrecision):
            if exponent := abs(math.ceil(math.log10(value - value_floor))):
                digits = compute_auto_precision_digits(exponent, self.precision.digits)
        return (
            round(value, min(digits, _MAX_DIGITS))
            if use_max_digits_for_labels
            else round(value, digits)
        )

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

    def _stringify_formatted_value(self, value: int | float) -> str:
        return str(value)

    @abc.abstractmethod
    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]: ...

    def _postformat(
        self,
        formatted_parts: Sequence[Preformatted],
        compute_auto_precision_digits: Callable[[int, int], int],
        use_max_digits_for_labels: bool,
    ) -> str:
        results = []
        for formatted in formatted_parts:
            text = self._stringify_formatted_value(
                self._apply_precision(
                    formatted.value,
                    compute_auto_precision_digits,
                    use_max_digits_for_labels,
                )
            )
            results.append(
                _join_numerical_value_and_unit(
                    *self._make_rendered_numerical_value_and_unit(
                        Formatted(
                            text.rstrip("0").rstrip(".") if "." in text else text,
                            formatted.prefix,
                            formatted.symbol,
                        )
                    )
                ).strip()
            )
        return " ".join(results)

    def render(self, value: int | float) -> str:
        sign = "" if value >= 0 else "-"
        postformatted = self._postformat(
            self._preformat(abs(value)),
            lambda exponent, digits: max(exponent + 1, digits),
            True,
        )
        return f"{sign}{postformatted}"

    @abc.abstractmethod
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]: ...

    @abc.abstractmethod
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]: ...

    def render_y_labels(
        self,
        *,
        min_y: int | float,
        max_y: int | float,
        mean_num_labels: float,
    ) -> Sequence[Label]:
        assert min_y >= 0
        assert max_y >= 0
        assert mean_num_labels >= 0

        if 0 < min_y < 1:
            min_y = 0
        elif min_y > 1:
            min_y = math.floor(min_y)

        delta = max_y - min_y

        if delta == 0 or mean_num_labels == 0:
            return []

        if max_y < 1:
            atoms = self._compute_small_y_label_atoms(delta)
        else:  # max_y >= 1
            atoms = self._compute_large_y_label_atoms(delta)

        if possible_atoms := [(a, q) for a in atoms if (q := int(delta // a))]:
            atom, quotient = min(possible_atoms, key=lambda t: abs(t[1] - mean_num_labels))
        else:
            atom = int(delta / mean_num_labels)
            quotient = int(delta // atom)

        first = self._preformat(min_y + atom)[0]
        return [
            Label(
                p,
                self._postformat(
                    self._preformat(p, use_prefix=first.prefix, use_symbol=first.symbol),
                    lambda exponent, digits: exponent + digits,
                    self.use_max_digits_for_labels,
                ),
            )
            for i in range(0 if min_y else 1, quotient + 1)
            for p in (min_y + atom * i,)
        ]


def _join_numerical_value_and_unit(
    numerical_value: str,
    unit: str,
) -> str:
    """
    >>> _join_numerical_value_and_unit("1", "s")
    '1 s'
    >>> _join_numerical_value_and_unit("1", "/s")
    '1/s'
    """
    return f"{numerical_value}{unit}" if unit.startswith("/") else f"{numerical_value} {unit}"


_BASIC_DECIMAL_ATOMS: Final = [1, 2, 5, 10, 20, 50]


def _stringify_small_decimal_number(value: float) -> str:
    assert value > 0
    text = str(value)
    if "e" not in text:
        return text
    decimals = math.floor(abs(math.log10(value)))
    int_part = text.split("e", 1)[0].replace(".", "")
    return f"0.{'0' * decimals}{int_part}"


@dataclass(frozen=True)
class DecimalFormatter(NotationFormatter):
    use_max_digits_for_labels: bool = False

    def ident(self) -> Literal["Decimal"]:
        return "Decimal"

    @property
    def js_formatter_name(self) -> Literal["DecimalFormatter"]:
        return "DecimalFormatter"

    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        return [Preformatted(value, "", self.symbol)]

    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[Preformatted]:
        return [Preformatted(value, "", self.symbol)]

    def _stringify_formatted_value(self, value: int | float) -> str:
        if 0 < abs(value) < 1:
            # For small decimal numbers we avoid the usage of Python's scientific notation if the
            # value is too small:
            # >>> str(.0001)
            # '0.0001'
            # >>> str(0.00001)
            # '1e-05'
            sign = "" if value > 0 else "-"
            return f"{sign}{_stringify_small_decimal_number(abs(value))}"
        return f"{value:,}".replace(
            ",",
            "\N{THIN SPACE}",
        )

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return formatted.text, formatted.symbol

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

    @property
    def js_formatter_name(self) -> Literal["SIFormatter"]:
        return "SIFormatter"

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

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return formatted.text, f"{formatted.prefix}{formatted.symbol}"

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

    @property
    def js_formatter_name(self) -> Literal["IECFormatter"]:
        return "IECFormatter"

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

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return formatted.text, f"{formatted.prefix}{formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        exponent = math.floor(math.log2(max_y))
        return [pow(2, e) for e in range(exponent + 1)]


class StandardScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["StandardScientific"]:
        return "StandardScientific"

    @property
    def js_formatter_name(self) -> Literal["StandardScientificFormatter"]:
        return "StandardScientificFormatter"

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

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return f"{formatted.text}{formatted.prefix}", formatted.symbol

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class EngineeringScientificFormatter(NotationFormatter):
    def ident(self) -> Literal["EngineeringScientific"]:
        return "EngineeringScientific"

    @property
    def js_formatter_name(self) -> Literal["EngineeringScientificFormatter"]:
        return "EngineeringScientificFormatter"

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

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return f"{formatted.text}{formatted.prefix}", formatted.symbol

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


_ONE_YEAR: Final = 31536000  # We use always 365 * 86400
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
    _ONE_YEAR,
    2 * _ONE_YEAR,
    5 * _ONE_YEAR,
    10 * _ONE_YEAR,
    20 * _ONE_YEAR,
    50 * _ONE_YEAR,
    100 * _ONE_YEAR,
]
_TIME_SMALL_PREFIXES: Final = [
    (-6, 2, "μ"),
    (-3, 1, "m"),
]
_TIME_LARGE_SYMBOLS: Final = [
    (_ONE_YEAR, "y"),
    (_ONE_DAY, "d"),
    (_ONE_HOUR, "h"),
    (_ONE_MINUTE, "min"),
]


class TimeFormatter(NotationFormatter):
    def ident(self) -> Literal["Time"]:
        return "Time"

    @property
    def js_formatter_name(self) -> Literal["TimeFormatter"]:
        return "TimeFormatter"

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
            case "y":
                years = int(rounded_value // _ONE_YEAR)
                formatted_parts.append(Preformatted(years, "", "y"))
                if days := round((rounded_value - years * _ONE_YEAR) / _ONE_DAY):
                    formatted_parts.append(Preformatted(days, "", "d"))
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

    def _make_rendered_numerical_value_and_unit(self, formatted: Formatted) -> tuple[str, str]:
        return formatted.text, f"{formatted.prefix}{formatted.symbol}"

    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        if max_y >= _ONE_YEAR:
            if (q := int(max_y // _ONE_YEAR)) < 5:
                return _BASIC_TIME_ATOMS[22:]
            exponent = math.floor(math.log10(q))
            return _BASIC_TIME_ATOMS[22:] + [
                _ONE_YEAR * a * pow(10, exponent - 1) for a in _BASIC_DECIMAL_ATOMS
            ]
        if max_y >= _ONE_DAY:
            return _BASIC_TIME_ATOMS[15:]
        if max_y >= _ONE_HOUR:
            return _BASIC_TIME_ATOMS[9:18]
        if max_y >= _ONE_MINUTE:
            return _BASIC_TIME_ATOMS[3:12]
        return _BASIC_DECIMAL_ATOMS[:6]
