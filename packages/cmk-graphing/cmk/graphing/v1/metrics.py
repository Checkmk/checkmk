#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from ._color import Color
from ._localize import Localizable
from ._unit import PhysicalUnit, ScientificUnit, Unit

__all__ = [
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


@dataclass(frozen=True, kw_only=True)
class Metric:
    """
    Defines a metric

    A metric can be used within :class:`WarningOf`, :class:`CriticalOf`, :class:`MinimumOf`,
    :class:`MaximumOf`, perfometers or graphs by its name.

    Args:
        name:   An unique name
        title:  A title
        unit:   A unit
        color:  A color

    Example:

        >>> metric_metric_name = Metric(
        ...     name="metric_name",
        ...     title=Localizable("A metric"),
        ...     unit=Unit.PERCENTAGE,
        ...     color=Color.BLUE,
        ... )

    """

    name: str
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class Constant:
    """
    Defines a constant

    A constant can be used within other metric operations, perfometers or graphs.

    Args:
        title:  A title
        unit:   A unit
        color:  A color
        value:  An integer or float value

    Example:

        >>> Constant(Localizable("A title"), Unit.COUNT, Color.BLUE, 23.5)
        Constant(title=Localizable('A title'), unit=<Unit.COUNT: ''>, color=<Color.BLUE: 14>, \
value=23.5)

    """

    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    value: int | float


@dataclass(frozen=True)
class WarningOf:
    """
    Defines a :class:`WarningOf`

    A :class:`WarningOf` extracts the warning level of a metric by its name. It can be used within
    metric other metric operations, perfometers or graphs.

    Args:
        metric_name:
                Name of a metric

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
    Defines a :class:`CriticalOf`

    A :class:`CriticalOf` extracts the critical level of a metric by its name. It can be used within
    other metric operations, perfometers or graphs.

    Args:
        metric_name:
                Name of a metric

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
    Defines a :class:`MinimumOf`

    A :class:`MinimumOf` extracts the minimum value of a metric by its name. It can be used within
    other metric operations, perfometers or graphs.

    Args:
        metric_name:
                Name of a metric
        color:  A color

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
    Defines a :class:`MaximumOf`

    A :class:`MaximumOf` extracts the maximum value of a metric by its name. It can be used within
    other metric operations, perfometers or graphs.

    Args:
        metric_name:
                Name of a metric
        color:  A color

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
    Defines a sum

    A sum can be used within other metric operations, perfometers or graphs.

    Args:
        title:  A title
        color:  A color
        summands:
                A list of metric names or objects

    Example:

        >>> Sum(
        ...     Localizable("A title"),
        ...     Color.BLUE,
        ...     ["metric-name-1", "metric-name-2"],
        ... )
        Sum(title=Localizable('A title'), color=<Color.BLUE: 14>, summands=['metric-name-1', \
'metric-name-2'])

    """

    title: Localizable
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
    Defines a product

    A product can be used within other metric operations, perfometers or graphs.

    Args:
        title:  A title
        unit:   A unit
        color:  A color
        factors:
                A list of metric names or objects

    Example:

        >>> Product(
        ...     Localizable("A title"),
        ...     Unit.COUNT,
        ...     Color.BLUE,
        ...     ["metric-name-1", "metric-name-2"],
        ... )
        Product(title=Localizable('A title'), unit=<Unit.COUNT: ''>, color=<Color.BLUE: 14>, \
factors=['metric-name-1', 'metric-name-2'])

    """

    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
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
    Defines a difference

    A difference can be used within other metric operations, perfometers or graphs.

    Args:
        title:  A title
        color:  A color
        minuend:
                A metric name or object
        subtrahend:
                A metric name or object

    Example:

        >>> Difference(
        ...     Localizable("A title"),
        ...     Color.BLUE,
        ...     minuend="metric-name-1",
        ...     subtrahend="metric-name-2",
        ... )
        Difference(title=Localizable('A title'), color=<Color.BLUE: 14>, minuend='metric-name-1', \
subtrahend='metric-name-2')

    """

    title: Localizable
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
    Defines a fraction

    A fraction can be used within other metric operations, perfometers or graphs.

    Args:
        title:  A title
        unit:   A unit
        color:  A color
        dividend:
                A metric name or object
        divisor:
                A metric name or object

    Example:

        >>> Fraction(
        ...     Localizable("A title"),
        ...     Unit.COUNT,
        ...     Color.BLUE,
        ...     dividend="metric-name-1",
        ...     divisor="metric-name-2",
        ... )
        Fraction(title=Localizable('A title'), unit=<Unit.COUNT: ''>, color=<Color.BLUE: 14>, \
dividend='metric-name-1', divisor='metric-name-2')

    """

    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
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
