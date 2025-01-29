#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_aws_http_500_rate = metrics.Metric(
    name="aws_http_500_rate",
    title=Title("HTTP 500 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_http_502_rate = metrics.Metric(
    name="aws_http_502_rate",
    title=Title("HTTP 502 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_http_503_rate = metrics.Metric(
    name="aws_http_503_rate",
    title=Title("HTTP 503 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_http_504_rate = metrics.Metric(
    name="aws_http_504_rate",
    title=Title("HTTP 504 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_http_50x_errors_rate = graphs.Graph(
    name="aws_http_50x_errors_rate",
    title=Title("HTTP 500/2/3/4 Errors"),
    compound_lines=[
        "aws_http_500_rate",
        "aws_http_502_rate",
        "aws_http_503_rate",
        "aws_http_504_rate",
    ],
)
