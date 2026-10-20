#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Self

from cmk.graphing_engine import (
    evaluate_graphs,
    Graph,
    prediction_window_of,
    PredictionTexts,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _

from ._graph_codec import GraphCodec
from ._graph_dispatch import (
    CommonGraphOptions,
    consolidation_function_of,
    edge_neighbours_at_served_step_of,
    EvaluatedGraphs,
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
    options: CommonGraphOptions
    fetch_data: FetchDataWithDiagnosticsProtocol

    @classmethod
    def make(cls, options: Mapping[str, object]) -> Self:
        return cls(
            CommonGraphOptions.from_request_options(options),
            PredictionFetchData(
                debug=active_config.debug,
                registered_translations=registered_translations(),
                edge_neighbours_at_served_step=edge_neighbours_at_served_step_of(options),
                consolidation_function=consolidation_function_of(options),
            ),
        )

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        return EvaluatedGraphs(
            graphs=evaluate_graphs(
                time_range=prediction_window_of(graph) or self.options.time_range,
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
