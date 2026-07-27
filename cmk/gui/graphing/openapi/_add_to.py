#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping

from cmk.gui.graphing._graph_specification import GraphSpecification, parse_graph_specification
from cmk.gui.openapi.utils import ProblemException


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
    # The add-to backends address a graph by its legacy specification, not by the engine's graph
    # definition: they store the specification and replay it whenever the target is rendered. Only
    # the graph kinds that declare an add_visual_type can be stored that way.
    def __init__(self, specification: GraphSpecification, add_type: str) -> None:
        self.specification = specification
        self.add_type = add_type

    @classmethod
    def parse(cls, specification: Mapping[str, object]) -> AddableGraph:
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
        return cls(parsed, add_type)

    def parameters(self) -> dict[str, object]:
        # The envelope the legacy "Add to ..." popup posts, of which every backend (dashboard,
        # report, graph collection, custom graph) reads the specification alone: the popup's
        # consolidation function and time range are dropped, the target supplies its own range.
        # So only the specification is sent, and the envelope's defaults cover the rest.
        return {"specification": self.specification.model_dump()}
