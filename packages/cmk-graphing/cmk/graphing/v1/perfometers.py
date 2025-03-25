#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from ._type_defs import Bound, Quantity

__all__ = [
    "Closed",
    "Open",
    "FocusRange",
    "Perfometer",
    "Bidirectional",
    "Stacked",
]


@dataclass(frozen=True)
class Closed:
    """
    Args:
        value: A bound value

    Example:

        >>> Closed(23.5)
        Closed(value=23.5)
    """

    value: Bound

    def __post_init__(self) -> None:
        if isinstance(self.value, str) and not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class Open:
    """
    Args:
        value: A bound value

    Example:

        >>> Open(23.5)
        Open(value=23.5)
    """

    value: Bound

    def __post_init__(self) -> None:
        if isinstance(self.value, str) and not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class FocusRange:
    """
    Args:
        lower: A lower bound
        upper: An upper bound

    For metric that only can produce values between 0 and 100, but never smaller or larger ones, use
    :class:`Closed` borders:

    >>> FocusRange(Closed(0), Closed(100))
    FocusRange(lower=Closed(value=0), upper=Closed(value=100))

    For metrics that can create arbitrarily small or large numbers, but you expect them to be
    between -10 and +10 most of the time, use :class:`Open` borders.

    >>> FocusRange(Open(-10), Open(+10))
    FocusRange(lower=Open(value=-10), upper=Open(value=10))
    """

    lower: Closed | Open
    upper: Closed | Open


@dataclass(frozen=True, kw_only=True)
class Perfometer:
    """
    Instances of this class will only be picked up by Checkmk if their names start with
    ``perfometer_``.

    Args:
        name: An unique name
        focus_range: A focus range
        segments: A list of metric names or objects

    Example:

        >>> perfometer_name = Perfometer(
        ...     name="name",
        ...     focus_range=FocusRange(Closed(0), Closed(100)),
        ...     segments=["metric-name-1", "metric-name-2"],
        ... )
    """

    name: str
    focus_range: FocusRange
    segments: Sequence[Quantity]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.segments
        for s in self.segments:
            if isinstance(s, str) and not s:
                raise ValueError(s)


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    """
    Instances of this class will only be picked up by Checkmk if their names start with
    ``perfometer_``.

    Args:
        name: An unique name
        left: A perfometer which grows to the left
        right: A perfometer which grows to the right

    Example:

        >>> perfometer_name = Bidirectional(
        ...     name="name",
        ...     left=Perfometer(
        ...         name="left",
        ...         focus_range=FocusRange(Closed(0), Closed(100)),
        ...         segments=["metric-name-1", "metric-name-2"],
        ...     ),
        ...     right=Perfometer(
        ...         name="right",
        ...         focus_range=FocusRange(Closed(0), Closed(50)),
        ...         segments=["metric-name-3"],
        ...     ),
        ... )
    """

    name: str
    left: Perfometer
    right: Perfometer

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True, kw_only=True)
class Stacked:
    """
    Instances of this class will only be picked up by Checkmk if their names start with
    ``perfometer_``.

    Args:
        name: An unique name
        lower: A perfometer at the bottom
        upper: A perfometer on the top

    Example:

        >>> perfometer_name = Stacked(
        ...     name="name",
        ...     lower=Perfometer(
        ...         name="lower",
        ...         focus_range=FocusRange(Closed(0), Closed(100)),
        ...         segments=["metric-name-1", "metric-name-2"],
        ...     ),
        ...     upper=Perfometer(
        ...         name="upper",
        ...         focus_range=FocusRange(Closed(0), Closed(50)),
        ...         segments=["metric-name-3"],
        ...     ),
        ... )
    """

    name: str
    lower: Perfometer
    upper: Perfometer

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
