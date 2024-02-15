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
    "Color",
    "Metric",
    "Constant",
    "WarningOf",
    "CriticalOf",
    "MinimumOf",
    "MaximumOf",
    "Sum",
    "Product",
    "Difference",
    "Fraction",
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


class Unit(Enum):
    # CMK
    BAR = auto()  # "bar"
    BIT_IEC = auto()  # "bits, factor 1024
    BIT_SI = auto()  # "bits, factor 1000
    BITS_IEC_PER_SECOND = auto()  # "bits/s, factor 1024
    BITS_SI_PER_SECOND = auto()  # "bits/s, factor 1000
    BYTE_IEC = auto()  # "bytes, factor 1024
    BYTE_SI = auto()  # "bytes, factor 1000
    BYTES_IEC_PER_SECOND = auto()  # "bytes/s, factor 1024
    BYTES_SI_PER_SECOND = auto()  # "bytes/s, factor 1000
    BYTES_IEC_PER_DAY = auto()  # "bytes/d, factor 1024
    BYTES_SI_PER_DAY = auto()  # "bytes/d, factor 1000
    BYTES_IEC_PER_OPERATION = auto()  # "bytes/op, factor 1024
    BYTES_SI_PER_OPERATION = auto()  # "bytes/op, factor 1000
    COUNT = auto()  # ", integer
    DECIBEL = auto()  # "dB"
    DECIBEL_MILLIVOLT = auto()  # "dBmV"
    DECIBEL_MILLIWATT = auto()  # "dBm"
    DOLLAR = auto()  # "$"
    ELETRICAL_ENERGY = auto()  # "Wh"
    EURO = auto()  # "€"
    LITER_PER_SECOND = auto()  # "l/s"
    NUMBER = auto()  # ", float
    PARTS_PER_MILLION = auto()  # "ppm"
    PERCENTAGE = auto()  # "%"
    PERCENTAGE_PER_METER = auto()  # "%/m"
    PER_SECOND = auto()  # "1/s"
    READ_CAPACITY_UNIT = auto()  # "RCU"
    REVOLUTIONS_PER_MINUTE = auto()  # "rpm"
    SECONDS_PER_SECOND = auto()  # "s/s"
    VOLT_AMPERE = auto()  # "VA"
    WRITE_CAPACITY_UNIT = auto()  # "WCU"
    # SI base unit
    AMPERE = auto()  # "A"
    CANDELA = auto()  # "cd"
    KELVIN = auto()  # "K"
    KILOGRAM = auto()  # "kg"
    METRE = auto()  # "m"
    MOLE = auto()  # "mol"
    SECOND = auto()  # "s"
    # SI Units with Special Names and Symbols
    BECQUEREL = auto()  # "Bq"
    COULOMB = auto()  # "C"
    DEGREE_CELSIUS = auto()  # "°C"
    FARAD = auto()  # "F"
    GRAY = auto()  # "Gy"
    HENRY = auto()  # "H"
    HERTZ = auto()  # "Hz"
    JOULE = auto()  # "J"
    KATAL = auto()  # "kat"
    LUMEN = auto()  # "lm"
    LUX = auto()  # "lx"
    NEWTON = auto()  # "N"
    OHM = auto()  # "Ω"
    PASCAL = auto()  # "Pa"
    RADIAN = auto()  # "rad"
    SIEMENS = auto()  # "S"
    SIEVERT = auto()  # "Sv"
    STERADIAN = auto()  # "sr"
    TESLA = auto()  # "T"
    VOLT = auto()  # "V"
    WATT = auto()  # "W"
    WEBER = auto()  # "Wb"


@dataclass(frozen=True)
class DecimalUnit:
    """
    A unit is rendered with decimals.
    """

    title: Title
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)


@dataclass(frozen=True)
class ScientificUnit:
    """
    A unit is using scientific notation while rendering.
    """

    title: Title
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)


@dataclass(frozen=True, kw_only=True)
class Metric:
    """
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
        ...     unit=Unit.PERCENTAGE,
        ...     color=Color.BLUE,
        ... )
    """

    name: str
    title: Title
    unit: Unit | DecimalUnit | ScientificUnit
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

        >>> Constant(Title("A title"), Unit.COUNT, Color.BLUE, 23.5)
        Constant(title=Title('A title'), unit=<Unit.COUNT: 14>, color=<Color.BLUE: 14>, \
value=23.5)
    """

    title: Title
    unit: Unit | DecimalUnit | ScientificUnit
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
        ...     Unit.COUNT,
        ...     Color.BLUE,
        ...     ["metric-name-1", "metric-name-2"],
        ... )
        Product(title=Title('A title'), unit=<Unit.COUNT: 14>, color=<Color.BLUE: 14>, \
factors=['metric-name-1', 'metric-name-2'])
    """

    title: Title
    unit: Unit | DecimalUnit | ScientificUnit
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
        ...     Unit.COUNT,
        ...     Color.BLUE,
        ...     dividend="metric-name-1",
        ...     divisor="metric-name-2",
        ... )
        Fraction(title=Title('A title'), unit=<Unit.COUNT: 14>, color=<Color.BLUE: 14>, \
dividend='metric-name-1', divisor='metric-name-2')
    """

    title: Title
    unit: Unit | DecimalUnit | ScientificUnit
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
