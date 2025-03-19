#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY
from enum import auto, Enum

from ._localize import Title

__all__ = [
    "AutoPrecision",
    "Color",
    "Constant",
    "CriticalOf",
    "DecimalNotation",
    "Difference",
    "EngineeringScientificNotation",
    "Fraction",
    "IECNotation",
    "MaximumOf",
    "Metric",
    "MinimumOf",
    "Product",
    "SINotation",
    "StandardScientificNotation",
    "StrictPrecision",
    "Sum",
    "TimeNotation",
    "Unit",
    "WarningOf",
]


class Color(Enum):
    LIGHT_RED = auto()
    RED = auto()
    DARK_RED = auto()

    LIGHT_ORANGE = auto()
    ORANGE = auto()
    DARK_ORANGE = auto()

    LIGHT_YELLOW = auto()
    YELLOW = auto()
    DARK_YELLOW = auto()

    LIGHT_GREEN = auto()
    GREEN = auto()
    DARK_GREEN = auto()

    LIGHT_BLUE = auto()
    BLUE = auto()
    DARK_BLUE = auto()

    LIGHT_CYAN = auto()
    CYAN = auto()
    DARK_CYAN = auto()

    LIGHT_PURPLE = auto()
    PURPLE = auto()
    DARK_PURPLE = auto()

    LIGHT_PINK = auto()
    PINK = auto()
    DARK_PINK = auto()

    LIGHT_BROWN = auto()
    BROWN = auto()
    DARK_BROWN = auto()

    LIGHT_GRAY = auto()
    GRAY = auto()
    DARK_GRAY = auto()

    BLACK = auto()
    WHITE = auto()


@dataclass(frozen=True)
class DecimalNotation:
    """
    A unit with decimal notation has no special format.
    """

    symbol: str


@dataclass(frozen=True)
class SINotation:
    """
    A unit with the SI notation formats a number with the following magnitudes:
    y, z, a, f, p, n, µ, m, "", k, M, G, T, P, E, Z, Y.
    """

    symbol: str


@dataclass(frozen=True)
class IECNotation:
    """
    A unit with the IEC notation formats a number with the following magnitudes:
    "", Ki, Mi, Gi, Ti, Pi, Ei, Zi, Yi.
    Positive number below one use the decimal notation.
    """

    symbol: str


@dataclass(frozen=True)
class StandardScientificNotation:
    """
    A unit with the standard scientific notation formats a number as following:
    m * 10**n, where 1 <= \\|m| < 10.
    """

    symbol: str


@dataclass(frozen=True)
class EngineeringScientificNotation:
    """
    A unit with the engineering scientific notation formats a number as following:
    m * 10**n, where 1 <= \\|m| < 1000 and n % 3 == 0.
    """

    symbol: str


@dataclass(frozen=True)
class TimeNotation:
    """
    A unit with the time notation formats a number with the following magnitudes:
    µs, ms, s, min, h, d, y.
    """

    @property
    def symbol(self) -> str:
        return "s"


@dataclass(frozen=True)
class AutoPrecision:
    """
    A unit with auto precision rounds the fractional part to the given digits or to the latest
    non-zero digit.
    """

    digits: int

    def __post_init__(self) -> None:
        if self.digits < 0:
            raise ValueError(self.digits)


@dataclass(frozen=True)
class StrictPrecision:
    """
    A unit with strict precision rounds the fractional part to the given digits.
    """

    digits: int

    def __post_init__(self) -> None:
        if self.digits < 0:
            raise ValueError(self.digits)


@dataclass(frozen=True)
class Unit:
    """
    Defines a unit which can be used within metrics and metric operations.

    Examples:

        >>> Unit(DecimalNotation(""), StrictPrecision(0))  # rendered as integer
        Unit(notation=DecimalNotation(symbol=''), precision=StrictPrecision(digits=0))

        >>> Unit(DecimalNotation(""), StrictPrecision(2))  # rendered as float with two digits
        Unit(notation=DecimalNotation(symbol=''), precision=StrictPrecision(digits=2))

        >>> Unit(SINotation("bytes"))  # bytes which are scaled with SI prefixes
        Unit(notation=SINotation(symbol='bytes'), precision=AutoPrecision(digits=2))

        >>> Unit(IECNotation("bits"))  # bits which are scaled with IEC prefixes
        Unit(notation=IECNotation(symbol='bits'), precision=AutoPrecision(digits=2))
    """

    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    )
    precision: AutoPrecision | StrictPrecision = AutoPrecision(2)


@dataclass(frozen=True, kw_only=True)
class Metric:
    """

    Instances of this class will only be picked up by Checkmk if their names start with ``metric_``.

    A metric can be used within :class:`WarningOf`, :class:`CriticalOf`, :class:`MinimumOf`,
    :class:`MaximumOf`, perfometers or graphs by its name.

    Args:
        name: An unique name
        title: A title
        unit: A unit
        color: A color

    Example:

        >>> metric_metric_name = Metric(
        ...     name="metric_name",
        ...     title=Title("A metric"),
        ...     unit=Unit(DecimalNotation("")),
        ...     color=Color.BLUE,
        ... )
    """

    name: str
    title: Title
    unit: Unit
    color: Color

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class Constant:
    """
    A constant can be used within other metric operations, perfometers or graphs.

    Args:
        title: A title
        unit: A unit
        color: A color
        value: An integer or float value

    Example:

        >>> Constant(
        ...     Title("A title"),
        ...     Unit(IECNotation("bits")),
        ...     Color.BLUE,
        ...     23.5,
        ... )
        Constant(title=Title('A title'), unit=Unit(notation=IECNotation(symbol='bits'),\
 precision=AutoPrecision(digits=2)), color=<Color.BLUE: 14>, value=23.5)
    """

    title: Title
    unit: Unit
    color: Color
    value: int | float


@dataclass(frozen=True)
class WarningOf:
    """
    Extracts the warning level of a metric by its name. It can be used within metric other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric

    Example:

        >>> WarningOf("metric-name")
        WarningOf(metric_name='metric-name')
    """

    metric_name: str

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)


@dataclass(frozen=True)
class CriticalOf:
    """
    Extracts the critical level of a metric by its name. It can be used within other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric

    Example:

        >>> CriticalOf("metric-name")
        CriticalOf(metric_name='metric-name')
    """

    metric_name: str

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)


@dataclass(frozen=True)
class MinimumOf:
    """
    Extracts the minimum value of a metric by its name. It can be used within other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric
        color: A color

    Example:

        >>> MinimumOf("metric-name", Color.BLUE)
        MinimumOf(metric_name='metric-name', color=<Color.BLUE: 14>)
    """

    metric_name: str
    color: Color

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)


@dataclass(frozen=True)
class MaximumOf:
    """
    Extracts the maximum value of a metric by its name. It can be used within other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric
        color: A color

    Example:

        >>> MaximumOf("metric-name", Color.BLUE)
        MaximumOf(metric_name='metric-name', color=<Color.BLUE: 14>)
    """

    metric_name: str
    color: Color

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError(self.metric_name)


@dataclass(frozen=True)
class Sum:
    """
    Defines the metric operation sum which can be used within other metric operations,
    perfometers or graphs.

    Args:
        title: A title
        color: A color
        summands: A list of metric names or objects

    Example:

        >>> Sum(
        ...     Title("A title"),
        ...     Color.BLUE,
        ...     ["metric-name-1", "metric-name-2"],
        ... )
        Sum(title=Title('A title'), color=<Color.BLUE: 14>, summands=['metric-name-1', \
'metric-name-2'])
    """

    title: Title
    color: Color
    summands: Sequence[
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    ]

    def __post_init__(self) -> None:
        assert self.summands
        for s in self.summands:
            if isinstance(s, str) and not s:
                raise ValueError(s)


@dataclass(frozen=True)
class Product:
    """
    Defines the metric operation product which can be used within other metric operations,
    perfometers or graphs.

    Args:
        title: A title
        unit: A unit
        color: A color
        factors: A list of metric names or objects

    Example:

        >>> Product(
        ...     Title("A title"),
        ...     Unit(IECNotation("bits")),
        ...     Color.BLUE,
        ...     ["metric-name-1", "metric-name-2"],
        ... )
        Product(title=Title('A title'), unit=Unit(notation=IECNotation(symbol='bits'),\
 precision=AutoPrecision(digits=2)), color=<Color.BLUE: 14>,\
 factors=['metric-name-1', 'metric-name-2'])
    """

    title: Title
    unit: Unit
    color: Color
    factors: Sequence[
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    ]

    def __post_init__(self) -> None:
        assert self.factors
        for f in self.factors:
            if isinstance(f, str) and not f:
                raise ValueError(f)


@dataclass(frozen=True)
class Difference:
    """
    Defines the metric operation difference which can be used within other metric operations,
    perfometers or graphs.

    Args:
        title: A title
        color: A color
        minuend: A metric name or object
        subtrahend: A metric name or object

    Example:

        >>> Difference(
        ...     Title("A title"),
        ...     Color.BLUE,
        ...     minuend="metric-name-1",
        ...     subtrahend="metric-name-2",
        ... )
        Difference(title=Title('A title'), color=<Color.BLUE: 14>, minuend='metric-name-1', \
subtrahend='metric-name-2')
    """

    title: Title
    color: Color
    _: KW_ONLY
    minuend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )
    subtrahend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )

    def __post_init__(self) -> None:
        if isinstance(self.minuend, str) and not self.minuend:
            raise ValueError(self.minuend)
        if isinstance(self.subtrahend, str) and not self.subtrahend:
            raise ValueError(self.subtrahend)


@dataclass(frozen=True)
class Fraction:
    """
    Defines the metric operation fraction which can be used within other metric operations,
    perfometers or graphs.

    Args:
        title: A title
        unit: A unit
        color: A color
        dividend: A metric name or object
        divisor: A metric name or object

    Example:

        >>> Fraction(
        ...     Title("A title"),
        ...     Unit(IECNotation("bits")),
        ...     Color.BLUE,
        ...     dividend="metric-name-1",
        ...     divisor="metric-name-2",
        ... )
        Fraction(title=Title('A title'), unit=Unit(notation=IECNotation(symbol='bits'),\
 precision=AutoPrecision(digits=2)), color=<Color.BLUE: 14>, dividend='metric-name-1',\
 divisor='metric-name-2')
    """

    title: Title
    unit: Unit
    color: Color
    _: KW_ONLY
    dividend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )
    divisor: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )

    def __post_init__(self) -> None:
        if isinstance(self.dividend, str) and not self.dividend:
            raise ValueError(self.dividend)
        if isinstance(self.divisor, str) and not self.divisor:
            raise ValueError(self.divisor)
