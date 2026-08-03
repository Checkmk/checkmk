#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping

from cmk.graphing_engine import Graph
from cmk.gui.graphing._engine_codec import ensure_type
from cmk.gui.graphing._engine_dispatch import engine_graph_dispatcher_registry
from cmk.gui.graphing._graph_specification import GraphSpecification, parse_graph_specification
from cmk.gui.openapi.utils import ProblemException


def parse_built_graph(internal: Mapping[str, object]) -> Graph:
    """The one graph a posted definition holds, decoded by the dispatcher of its kind."""
    serialized = ensure_type(internal["graphs"], list)
    if len(serialized) != 1:
        raise ProblemException(
            status=400,
            title="Not a single graph",
            detail=f"Expected exactly one graph, got {len(serialized)}.",
        )
    graph = ensure_type(serialized[0], dict)
    try:
        dispatcher = engine_graph_dispatcher_registry[ensure_type(graph["kind"], str)]
    except KeyError as exc:
        raise ProblemException(
            status=400,
            title="Unknown graph kind",
            detail=f"There is no graph kind {exc}.",
        ) from exc
    return dispatcher.deserialize(graph)


def parse_specification(specification: Mapping[str, object]) -> GraphSpecification:
    try:
        return parse_graph_specification(dict(specification))
    except (ValueError, TypeError, KeyError) as exc:
        raise ProblemException(
            status=400,
            title="Invalid graph specification",
            detail=f"Cannot parse the graph specification: {exc}",
        ) from exc


class AddableGraph:
    # Most add-to backends address a graph by its legacy specification, not by the engine's graph
    # definition: they store the specification and replay it whenever the target is rendered. Only
    # the graph kinds that declare an add_visual_type can be stored that way. A container that
    # stores what a graph is made of takes the built graph instead, so both travel along.
    def __init__(
        self, specification: GraphSpecification, add_type: str, built: Graph | None = None
    ) -> None:
        self.specification = specification
        self.add_type = add_type
        self.built = built

    @classmethod
    def parse(
        cls, specification: Mapping[str, object], internal: Mapping[str, object] | None = None
    ) -> AddableGraph:
        parsed = parse_specification(specification)
        if (add_type := parsed.add_visual_type()) is None:
            raise ProblemException(
                status=400,
                title="Graph cannot be added",
                detail=(
                    f"Graphs of type '{parsed.graph_type}' offer no add-to action. Only graphs "
                    "carrying a specification with an add-to type can be stored in a visual or "
                    "container."
                ),
            )
        return cls(parsed, add_type, None if internal is None else parse_built_graph(internal))

    def parameters(self) -> dict[str, object]:
        # The envelope the legacy "Add to ..." popup posts, of which most backends (dashboard,
        # report, graph collection) read the specification alone: the popup's consolidation
        # function and time range are dropped, the target supplies its own range. A custom graph
        # stores the curves a graph is made of, so it reads the built graph when one came along.
        parameters: dict[str, object] = {"specification": self.specification.model_dump()}
        if self.built is not None:
            parameters["built_graph"] = self.built
        return parameters
