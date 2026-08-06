#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The graph discovery contract: what a built graph is, and what resolving a specification to the
# data-less graphs it matches hands back. Each edition discovers its own kinds against it; both the
# REST discovery endpoints and the dashboard graph widgets go through them, so the interactive and
# the shared (token-authenticated) dashboard resolve the same graphs.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine import Graph

from ._graph_specification import GraphSpecification


@dataclass(frozen=True)
class BuiltGraph:
    # An engine graph bundled with the legacy specification it can be added to (dashboard, report,
    # graph collection, custom graph). ``specification`` is None for graph kinds that offer no "Add
    # to" action; otherwise it carries the concrete per-graph specification the add-to endpoints
    # replay.
    graph: Graph
    specification: GraphSpecification | None


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
