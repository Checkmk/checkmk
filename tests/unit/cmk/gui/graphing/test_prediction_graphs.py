#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    build_prediction_graph,
    Graph,
    HostName,
    MetricName,
    prediction_window_of,
    PredictionGraphContext,
    ServiceName,
    SiteID,
)
from cmk.gui.graphing._graph_codec import community_graph_codec
from cmk.gui.graphing._prediction_graphs import PREDICTION_KIND, prediction_texts


def _graph() -> Graph:
    return build_prediction_graph(
        PredictionGraphContext(
            site_id=SiteID("heute"),
            host_name=HostName("h"),
            service_name=ServiceName("svc"),
            metric_name=MetricName("util"),
            period="wday",
            valid_from=1700000000,
            valid_until=1700086400,
            directions=("upper", "lower"),
        ),
        title="Prediction",
        metrics={},
        kind=PREDICTION_KIND,
        texts=prediction_texts(),
        localizer=str,
    )


def test_the_window_survives_the_trip_through_the_browser() -> None:
    codec = community_graph_codec()

    restored = codec.deserialize_graph(codec.serialize_graph(_graph()))

    assert prediction_window_of(restored) == prediction_window_of(_graph())
