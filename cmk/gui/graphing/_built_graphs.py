#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine import FixedRange, Graph
from cmk.shared_typing.cmk_time_series_graph import UnitFormat

from ._graph_specification import GraphSpecification


@dataclass(frozen=True)
class BuiltGraph:
    # An engine graph bundled with the legacy specification it can be added to (dashboard, report,
    # graph collection, custom graph). ``specification`` is None for graph kinds that offer no "Add
    # to" action; otherwise it carries the concrete per-graph specification the add-to endpoints
    # replay.
    graph: Graph
    specification: GraphSpecification | None
    y_axis_unit: UnitFormat | None = None

    def y_axis_bounds(self) -> tuple[float, float] | None:
        """The edges the value axis is pinned to; None to scale it to the values that are drawn."""
        match self.graph.vertical_range:
            case FixedRange(lower=int() | float() as lower, upper=int() | float() as upper):
                return lower, upper
            case _:
                # A minimal range only widens the drawn extent, and a bound the engine resolves
                # while evaluating is no edge a data-less shell can name.
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
