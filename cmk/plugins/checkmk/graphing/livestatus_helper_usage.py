#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_helper_usage_fetcher = metrics.Metric(
    name="helper_usage_fetcher",
    title=Title("Fetcher helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)
metric_helper_usage_checker = metrics.Metric(
    name="helper_usage_checker",
    title=Title("Checker helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_helper_usage_generic = metrics.Metric(
    name="helper_usage_generic",
    title=Title("Active check helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

graph_helper_usage = graphs.Graph(
    name="helper_usage",
    title=Title("Helper usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    simple_lines=[
        "helper_usage_fetcher",
        "helper_usage_checker",
        "helper_usage_generic",
    ],
)
