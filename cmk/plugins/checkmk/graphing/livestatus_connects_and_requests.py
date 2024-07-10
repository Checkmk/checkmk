#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_livestatus_request_rate = metrics.Metric(
    name="livestatus_request_rate",
    title=Title("Livestatus requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_livestatus_connect_rate = metrics.Metric(
    name="livestatus_connect_rate",
    title=Title("Livestatus connects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_livestatus_requests_per_connection = graphs.Graph(
    name="livestatus_requests_per_connection",
    title=Title("Livestatus requests per connection"),
    compound_lines=[
        metrics.Fraction(
            Title("Average requests per connection"),
            UNIT_NUMBER,
            metrics.Color.ORANGE,
            dividend="livestatus_request_rate",
            divisor=metrics.Sum(
                Title("Average requests per connection"),
                metrics.Color.GRAY,
                [
                    "livestatus_connect_rate",
                    metrics.Constant(
                        Title(""),
                        UNIT_NUMBER,
                        metrics.Color.GRAY,
                        1e-16,
                    ),
                ],
            ),
        )
    ],
)
graph_livestatus_connects_and_requests = graphs.Graph(
    name="livestatus_connects_and_requests",
    title=Title("Livestatus connects and requests"),
    simple_lines=[
        "livestatus_request_rate",
        "livestatus_connect_rate",
    ],
)
