#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Final, Literal, override

from pydantic import BaseModel

_MAX_DIGITS: Final = 5


@dataclass(frozen=True)
class _PreFormattedPart:
    value: int | float
    prefix: str
    symbol: str


@dataclass(frozen=True, kw_only=True)
class FormattedPart:
    text: str
    unit: str


def _join_text_and_unit(formatted_part: FormattedPart) -> str:
    """
    >>> _join_text_and_unit(FormattedPart(text="1", unit="s"))
    '1 s'
    >>> _join_text_and_unit(FormattedPart(text="1", unit="/s"))
    '1/s'
    """
    return (
        f"{formatted_part.text}{formatted_part.unit}"
        if formatted_part.unit.startswith("/")
        else f"{formatted_part.text} {formatted_part.unit}"
    )


@dataclass(frozen=True, kw_only=True)
class Formatted:
    sign: Literal["", "-"]
    parts: Sequence[FormattedPart]

    def render(self) -> str:
        return f"{self.sign}{' '.join(_join_text_and_unit(f).strip() for f in self.parts)}"


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


@dataclass(frozen=True, kw_only=True)
class PositiveYRange:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start < 0 or self.start > self.end:
            raise ValueError("PositiveRange must have 0 <= start <= end")


@dataclass(frozen=True, kw_only=True)
class NegativeYRange:
    start: float
    end: float

    def __post_init__(self) -> None:
        if self.start > 0 or self.start > self.end:
            raise ValueError("NegativeRange must have start <= end <= 0")


@dataclass(frozen=True)
class NotationFormatter(abc.ABC):
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
    ) -> Sequence[_PreFormattedPart]: ...

    @abc.abstractmethod
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]: ...

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
    ) -> Sequence[_PreFormattedPart]:
        assert value >= 0
        if value in (0, 1):
            return [_PreFormattedPart(value, "", self.symbol)]
        if value < 1:
            return self._preformat_small_number(value, use_prefix, use_symbol)
        # value > 1
        return self._preformat_large_number(value, use_prefix, use_symbol)

    def _stringify_formatted_value(self, value: int | float) -> str:
        return str(value)

    @abc.abstractmethod
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart: ...

    def _postformat(
        self,
        pre_formatted_parts: Sequence[_PreFormattedPart],
        compute_auto_precision_digits: Callable[[int, int], int],
        use_max_digits_for_labels: bool,
    ) -> Iterator[FormattedPart]:
        for part in pre_formatted_parts:
            text = self._stringify_formatted_value(
                self._apply_precision(
                    part.value,
                    compute_auto_precision_digits,
                    use_max_digits_for_labels,
                )
            )
            yield self._format_text_and_unit(
                text=text.rstrip("0").rstrip(".") if "." in text else text,
                prefix=part.prefix,
                symbol=part.symbol,
            )

    def render(self, value: int | float) -> str:
        return Formatted(
            sign="" if value >= 0 else "-",
            parts=list(
                self._postformat(
                    self._preformat(abs(value)),
                    lambda exponent, digits: max(exponent + 1, digits),
                    True,
                )
            ),
        ).render()

    @abc.abstractmethod
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]: ...

    @abc.abstractmethod
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]: ...

    def render_y_labels(
        self,
        y_range: PositiveYRange | NegativeYRange,
        target_number_of_labels: float,
    ) -> Sequence[Label]:
        assert target_number_of_labels >= 0

        if isinstance(y_range, PositiveYRange):
            y_start_pos_rounded = math.floor(y_range.start)
            y_end_pos = y_range.end
            sign_text: Literal["", "-"] = ""
            sign_number = 1
        else:
            y_start_pos_rounded = math.floor(-y_range.end)
            y_end_pos = -y_range.start
            sign_text = "-"
            sign_number = -1

        delta = y_end_pos - y_start_pos_rounded
        if delta == 0 or target_number_of_labels == 0:
            return []

        atoms = (
            self._compute_small_y_label_atoms
            if y_end_pos < 1
            else self._compute_large_y_label_atoms
        )(delta)

        if possible_atoms := [
            (a, n_labels_for_atom) for a in atoms if (n_labels_for_atom := int(delta // a))
        ]:
            selected_atom, _n_labels_for_selected_atom = min(
                possible_atoms, key=lambda t: abs(t[1] - target_number_of_labels)
            )
        else:
            selected_atom = int(delta / target_number_of_labels)

        position_of_first_label = y_start_pos_rounded - y_start_pos_rounded % selected_atom
        n_labels = int((y_end_pos - position_of_first_label) // selected_atom)
        first_formatted_label = self._preformat(
            position_of_first_label or (position_of_first_label + selected_atom)
        )[0]

        return [
            Label(0, "0")
            if label_position == 0
            else Label(
                sign_number * label_position,
                Formatted(
                    sign=sign_text,
                    parts=list(
                        self._postformat(
                            self._preformat(
                                label_position,
                                use_prefix=first_formatted_label.prefix,
                                use_symbol=first_formatted_label.symbol,
                            ),
                            lambda exponent, digits: exponent + digits,
                            self.use_max_digits_for_labels,
                        )
                    ),
                ).render(),
            )
            for label_position in (
                position_of_first_label + selected_atom * i for i in range(n_labels + 1)
            )
        ]


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

    @override
    def ident(self) -> Literal["Decimal"]:
        return "Decimal"

    @property
    @override
    def js_formatter_name(self) -> Literal["DecimalFormatter"]:
        return "DecimalFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
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
        return f"{value:,}".replace(",", "\N{THIN SPACE}")

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=text, unit=symbol)

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
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
    @override
    def ident(self) -> Literal["SI"]:
        return "SI"

    @property
    @override
    def js_formatter_name(self) -> Literal["SIFormatter"]:
        return "SIFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _SI_SMALL_PREFIXES)
            return [_PreFormattedPart(value * pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value)) - 1
        for exp, power, prefix in _SI_SMALL_PREFIXES:
            if exponent <= exp:
                return [_PreFormattedPart(value * pow(1000, power), prefix, self.symbol)]
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _SI_LARGE_PREFIXES)
            return [_PreFormattedPart(value / pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value))
        for exp, power, prefix in _SI_LARGE_PREFIXES:
            if exponent >= exp:
                return [_PreFormattedPart(value / pow(1000, power), prefix, self.symbol)]
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=text, unit=f"{prefix}{symbol}")

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
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
    @override
    def ident(self) -> Literal["IEC"]:
        return "IEC"

    @property
    @override
    def js_formatter_name(self) -> Literal["IECFormatter"]:
        return "IECFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _IEC_LARGE_PREFIXES)
            return [_PreFormattedPart(value / pow(1024, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log2(value))
        for exp, power, prefix in _IEC_LARGE_PREFIXES:
            if exponent >= exp:
                return [_PreFormattedPart(value / pow(1024, power), prefix, self.symbol)]
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=text, unit=f"{prefix}{symbol}")

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        exponent = math.floor(math.log2(max_y))
        return [pow(2, e) for e in range(exponent + 1)]


class StandardScientificFormatter(NotationFormatter):
    @override
    def ident(self) -> Literal["StandardScientific"]:
        return "StandardScientific"

    @property
    @override
    def js_formatter_name(self) -> Literal["StandardScientificFormatter"]:
        return "StandardScientificFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        exponent = math.floor(math.log10(value))
        return [_PreFormattedPart(value / pow(10, exponent), f"e{exponent}", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        exponent = math.floor(math.log10(value))
        return [_PreFormattedPart(value / pow(10, exponent), f"e+{exponent}", self.symbol)]

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=f"{text}{prefix}", unit=symbol)

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
    def _compute_large_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]


class EngineeringScientificFormatter(NotationFormatter):
    @override
    def ident(self) -> Literal["EngineeringScientific"]:
        return "EngineeringScientific"

    @property
    @override
    def js_formatter_name(self) -> Literal["EngineeringScientificFormatter"]:
        return "EngineeringScientificFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        exponent = math.floor(math.log10(value) / 3) * 3
        return [_PreFormattedPart(value / pow(10, exponent), f"e{exponent}", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        exponent = math.floor(math.log10(value) // 3) * 3
        return [_PreFormattedPart(value / pow(10, exponent), f"e+{exponent}", self.symbol)]

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=f"{text}{prefix}", unit=symbol)

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
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
    @override
    def ident(self) -> Literal["Time"]:
        return "Time"

    @property
    @override
    def js_formatter_name(self) -> Literal["TimeFormatter"]:
        return "TimeFormatter"

    @override
    def _preformat_small_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        if use_prefix:
            power = _find_prefix_power(use_prefix, _TIME_SMALL_PREFIXES)
            return [_PreFormattedPart(value * pow(1000, power), use_prefix, self.symbol)]
        exponent = math.floor(math.log10(value)) - 1
        for exp, power, prefix in _TIME_SMALL_PREFIXES:
            if exponent <= exp:
                return [_PreFormattedPart(value * pow(1000, power), prefix, self.symbol)]
        return [_PreFormattedPart(value, "", self.symbol)]

    @override
    def _preformat_large_number(
        self, value: int | float, use_prefix: str, use_symbol: str
    ) -> Sequence[_PreFormattedPart]:
        if not use_symbol:
            for factor, symbol in _TIME_LARGE_SYMBOLS:
                if value >= factor:
                    use_symbol = symbol
                    break
        rounded_value = round(value)
        pre_formatted_parts = []
        match use_symbol:
            case "y":
                years = int(rounded_value // _ONE_YEAR)
                pre_formatted_parts.append(_PreFormattedPart(years, "", "y"))
                if days := round((rounded_value - years * _ONE_YEAR) / _ONE_DAY):
                    pre_formatted_parts.append(_PreFormattedPart(days, "", "d"))
            case "d":
                days = int(rounded_value // _ONE_DAY)
                pre_formatted_parts.append(_PreFormattedPart(days, "", "d"))
                if days < 10 and (hours := round((rounded_value - days * _ONE_DAY) / _ONE_HOUR)):
                    pre_formatted_parts.append(_PreFormattedPart(hours, "", "h"))
            case "h":
                hours = int(rounded_value // _ONE_HOUR)
                pre_formatted_parts.append(_PreFormattedPart(hours, "", "h"))
                if minutes := round((rounded_value - hours * _ONE_HOUR) / _ONE_MINUTE):
                    pre_formatted_parts.append(_PreFormattedPart(minutes, "", "min"))
            case "min":
                minutes = int(rounded_value // _ONE_MINUTE)
                pre_formatted_parts.append(_PreFormattedPart(minutes, "", "min"))
                if seconds := round(rounded_value - minutes * _ONE_MINUTE):
                    pre_formatted_parts.append(_PreFormattedPart(seconds, "", "s"))
            case _:
                pre_formatted_parts.append(_PreFormattedPart(value, "", "s"))
        return pre_formatted_parts

    @override
    def _format_text_and_unit(self, *, text: str, prefix: str, symbol: str) -> FormattedPart:
        return FormattedPart(text=text, unit=f"{prefix}{symbol}")

    @override
    def _compute_small_y_label_atoms(self, max_y: int | float) -> Sequence[int | float]:
        factor = pow(10, math.floor(math.log10(max_y)) - 1)
        return [a * factor for a in _BASIC_DECIMAL_ATOMS]

    @override
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
