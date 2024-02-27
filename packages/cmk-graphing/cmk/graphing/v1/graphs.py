#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from ._localize import Title
from ._type_defs import Bound, Quantity

__all__ = [
    "MinimalRange",
    "Graph",
    "Bidirectional",
]


@dataclass(frozen=True)
class MinimalRange:
    """
    The minimal range describes what will at least be covered by the graphs vertical axis,
    regardless of the metrics values.
    The vertical axis will be extended if the metrics exceed the minimal range, but it will never be
    smaller.

    Args:
        lower: A lower bound
        upper: An upper bound

    Example:

        >>> MinimalRange(0, 100)
        MinimalRange(lower=0, upper=100)
    """

    lower: Bound
    upper: Bound

    def __post_init__(self) -> None:
        if isinstance(self.lower, str) and not self.lower:
            raise ValueError(self.lower)
        if isinstance(self.upper, str) and not self.upper:
            raise ValueError(self.upper)


@dataclass(frozen=True, kw_only=True)
class Graph:
    """
    Instances of this class will only be picked up by Checkmk if their names start with ``graph_``.

    Args:
        name: A unique name
        title: A title
        minimal_range: A minimal range
        compound_lines: A list of metric names or objects.
            These will constitute compound lines: Colored areas, stacked on top of each other.
        simple_lines: A list of metric names or objects.
            These will be rendered as simple lines, without colored areas.
        optional: A list of metric names.
            This graph template will be used, even if the metrics specified here are missing.
        conflicting: A list of metric names.
            This graph template will never be used if any of these metrics are created by the
            plugin.

    Example:

        >>> graph_name = Graph(
        ...     name="name",
        ...     title=Title("A title"),
        ...     minimal_range=MinimalRange(0, 100),
        ...     compound_lines=["metric-name-1"],
        ...     simple_lines=["metric-name-2"],
        ...     optional=["metric-name-1"],
        ...     conflicting=["metric-name-3"],
        ... )
    """

    name: str
    title: Title
    minimal_range: MinimalRange | None = None
    compound_lines: Sequence[Quantity] = ()
    simple_lines: Sequence[Quantity] = ()
    optional: Sequence[str] = ()
    conflicting: Sequence[str] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.compound_lines or self.simple_lines
        for c in self.compound_lines:
            if isinstance(c, str) and not c:
                raise ValueError(c)
        for s in self.simple_lines:
            if isinstance(s, str) and not s:
                raise ValueError(s)
        for o in self.optional:
            if isinstance(o, str) and not o:
                raise ValueError(o)
        for c in self.conflicting:
            if isinstance(c, str) and not c:
                raise ValueError(c)


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    """
    Instances of this class will only be picked up by Checkmk if their names start with ``graph_``.

    Args:
        name: A unique name
        title: A title
        lower: A graph which grows downwards
        upper: A graph which grows upwards

    Example:

        >>> graph_name = Bidirectional(
        ...     name="name",
        ...     title=Title("A title"),
        ...     lower=Graph(
        ...         name="lower",
        ...         title=Title("A title"),
        ...         compound_lines=["metric-name-1"],
        ...     ),
        ...     upper=Graph(
        ...         name="upper",
        ...         title=Title("A title"),
        ...         compound_lines=["metric-name-2"],
        ...     ),
        ... )
    """

    name: str
    title: Title
    lower: Graph
    upper: Graph

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
