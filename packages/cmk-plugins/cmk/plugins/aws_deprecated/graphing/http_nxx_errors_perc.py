#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_aws_http_2xx_perc = metrics.Metric(
    name="aws_http_2xx_perc",
    title=Title("Percentage of HTTP 2XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)

metric_aws_http_3xx_perc = metrics.Metric(
    name="aws_http_3xx_perc",
    title=Title("Percentage of HTTP 3XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_aws_http_4xx_perc = metrics.Metric(
    name="aws_http_4xx_perc",
    title=Title("Percentage of HTTP 4XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_http_5xx_perc = metrics.Metric(
    name="aws_http_5xx_perc",
    title=Title("Percentage of HTTP 5XX errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_http_nxx_errors_perc = graphs.Graph(
    name="aws_http_nxx_errors_perc",
    title=Title("Percentage of HTTP 3/4/5XX Errors"),
    compound_lines=[
        "aws_http_2xx_perc",
        "aws_http_3xx_perc",
        "aws_http_4xx_perc",
        "aws_http_5xx_perc",
    ],
    optional=[
        "aws_http_2xx_perc",
        "aws_http_3xx_perc",
    ],
)
