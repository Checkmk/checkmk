#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine import (
    drawn_curves,
    FixedRange,
    Graph,
    MinimalRange,
    NonConvertibleUnit,
    Unit,
)

from ._graph_specification import GraphSpecification


def _numeric_bound(bound: object) -> float | None:
    return float(bound) if isinstance(bound, int | float) else None


@dataclass(frozen=True)
class FixedAxisRange:
    lower: float
    upper: float


@dataclass(frozen=True)
class MinimalAxisRange:
    lower: float | None
    upper: float | None


@dataclass(frozen=True)
class BuiltGraph:
    # An engine graph bundled with the legacy specification it can be added to (dashboard, report,
    # graph collection, custom graph). ``specification`` is None for graph kinds that offer no "Add
    # to" action; otherwise it carries the concrete per-graph specification the add-to endpoints
    # replay.
    graph: Graph
    specification: GraphSpecification | None
    y_axis_unit: Unit | NonConvertibleUnit | None = None

    def resolved_y_axis_unit(self) -> Unit | NonConvertibleUnit | None:
        if self.y_axis_unit is not None:
            return self.y_axis_unit
        return next(
            (
                drawn.curve.attributes.unit
                for drawn in drawn_curves(self.graph.stacks, self.graph.lines)
            ),
            None,
        )

    def y_axis_range(self) -> FixedAxisRange | MinimalAxisRange | None:
        """The values the value axis spans; None to scale it to the values that are drawn."""
        match self.graph.vertical_range:
            case FixedRange(lower=int() | float() as lower, upper=int() | float() as upper):
                return FixedAxisRange(lower=lower, upper=upper)
            case MinimalRange(lower=lower, upper=upper):
                minimal = MinimalAxisRange(lower=_numeric_bound(lower), upper=_numeric_bound(upper))
                return None if minimal == MinimalAxisRange(lower=None, upper=None) else minimal
            case _:
                return None


@dataclass(frozen=True)
class DiscoveredGraphs:
    """The data-less graphs a specification matched.

    An empty match is an expected state (nothing monitored, no matching template, ...), not a
    failure: `no_data_message` then explains it in the caller's language. Failures - a dead
    monitoring core, a broken specification - are raised instead.
    """

    graphs: Sequence[BuiltGraph]
    no_data_message: str | None

    @classmethod
    def found(cls, graphs: Sequence[BuiltGraph]) -> DiscoveredGraphs:
        return cls(graphs=graphs, no_data_message=None)

    @classmethod
    def nothing(cls, no_data_message: str) -> DiscoveredGraphs:
        return cls(graphs=[], no_data_message=no_data_message)
