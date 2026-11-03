#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from cmk.graphing_engine import evaluate_graphs, Graph, TimeRange

from ._graph_dispatch import EvaluatedGraphs, FetchDataWithDiagnosticsProtocol


def requested_window(graph: Graph) -> TimeRange | None:  # noqa: ARG001
    return None


@dataclass(frozen=True)
class EvaluateGraph:
    time_range: TimeRange
    fetch_data: FetchDataWithDiagnosticsProtocol
    window_of: Callable[[Graph], TimeRange | None]

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        return EvaluatedGraphs(
            graphs=evaluate_graphs(
                time_range=self.window_of(graph) or self.time_range,
                graphs=[graph],
                fetch_data=self.fetch_data,
            ),
            diagnostics=self.fetch_data.diagnostics,
        )
