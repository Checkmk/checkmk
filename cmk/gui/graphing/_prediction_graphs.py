#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.graphing_engine import (
    prediction_window_of,
    PredictionTexts,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _

from ._evaluation_options import EvaluationOptions
from ._graph_codec import GraphCodec
from ._graph_dispatch import (
    GraphDispatcher,
)
from ._graph_evaluation import EvaluateGraph
from ._prediction_source import PredictionFetchData
from ._source import (
    FetchDiagnostics,
    rrd_fetch_data,
    RRDFetchPerformanceData,
    RRDFetchTimeSeries,
)

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


def _evaluate_prediction(options: EvaluationOptions) -> EvaluateGraph:
    diagnostics = FetchDiagnostics()
    return EvaluateGraph(
        options.time_range,
        PredictionFetchData(
            rrd=rrd_fetch_data(
                options, RRDFetchPerformanceData(), RRDFetchTimeSeries(), debug=active_config.debug
            ),
            debug=active_config.debug,
            diagnostics=diagnostics,
        ),
        window_of=prediction_window_of,
        diagnostics=diagnostics,
    )


def prediction_graph_dispatcher(codec: GraphCodec) -> GraphDispatcher:
    return GraphDispatcher(
        kind=PREDICTION_KIND,
        codec=codec,
        make_evaluate=_evaluate_prediction,
    )
