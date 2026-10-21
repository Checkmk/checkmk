#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Final, Self

from cmk.graphing_engine import (
    evaluate_graphs,
    Graph,
    prediction_window_of,
    PredictionTexts,
    TimeRange,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _

from ._graph_codec import GraphCodec
from ._graph_dispatch import (
    EvaluatedGraphs,
    EvaluationOptions,
    FetchDataWithDiagnosticsProtocol,
    GraphDispatcher,
)
from ._plugins import registered_translations
from ._prediction_source import PredictionFetchData

PREDICTION_KIND: Final = "prediction"


def prediction_texts() -> PredictionTexts:
    return PredictionTexts(
        prediction=_("Prediction"),
        ok_area=_("OK area"),
        warning_area=_("Warning area"),
        critical_area=_("Critical area"),
        upper_area=_("%(area)s (upper)"),
        lower_area=_("%(area)s (lower)"),
    )


@dataclass(frozen=True)
class _EvaluatePrediction:
    time_range: TimeRange
    fetch_data: FetchDataWithDiagnosticsProtocol

    @classmethod
    def make(cls, options: EvaluationOptions) -> Self:
        return cls(
            options.time_range,
            PredictionFetchData(
                debug=active_config.debug,
                registered_translations=registered_translations(),
                include_edge_neighbours=options.include_edge_neighbours,
                consolidation_function=options.consolidation_function,
            ),
        )

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        return EvaluatedGraphs(
            graphs=evaluate_graphs(
                time_range=prediction_window_of(graph) or self.time_range,
                graphs=[graph],
                fetch_data=self.fetch_data,
            ),
            diagnostics=self.fetch_data.diagnostics,
        )


def prediction_graph_dispatcher(codec: GraphCodec) -> GraphDispatcher:
    return GraphDispatcher(
        kind=PREDICTION_KIND,
        codec=codec,
        make_evaluate=_EvaluatePrediction.make,
    )
