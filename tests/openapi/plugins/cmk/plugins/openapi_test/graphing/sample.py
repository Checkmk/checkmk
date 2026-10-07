#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

METRIC_NAME = "openapi_test_metric"
METRIC_TITLE = "Test metric"
GRAPH_NAME = "openapi_test_graph"

metric_openapi_test = metrics.Metric(
    name=METRIC_NAME,
    title=Title("Test metric"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.LIGHT_BLUE,
)

graph_openapi_test = graphs.Graph(
    name=GRAPH_NAME,
    title=Title("Test graph"),
    compound_lines=[METRIC_NAME],
)
