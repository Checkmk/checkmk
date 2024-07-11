#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_aws_http_2xx_rate = metrics.Metric(
    name="aws_http_2xx_rate",
    title=Title("HTTP 2XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)

metric_aws_http_3xx_rate = metrics.Metric(
    name="aws_http_3xx_rate",
    title=Title("HTTP 3XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_aws_http_4xx_rate = metrics.Metric(
    name="aws_http_4xx_rate",
    title=Title("HTTP 4XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_http_5xx_rate = metrics.Metric(
    name="aws_http_5xx_rate",
    title=Title("HTTP 5XX errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_http_nxx_errors_rate = graphs.Graph(
    name="aws_http_nxx_errors_rate",
    title=Title("HTTP 3/4/5XX Errors"),
    compound_lines=[
        "aws_http_2xx_rate",
        "aws_http_3xx_rate",
        "aws_http_4xx_rate",
        "aws_http_5xx_rate",
    ],
    optional=[
        "aws_http_2xx_rate",
        "aws_http_3xx_rate",
    ],
)
