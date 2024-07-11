#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_aws_http_500_perc = metrics.Metric(
    name="aws_http_500_perc",
    title=Title("Percentage of HTTP 500 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_http_502_perc = metrics.Metric(
    name="aws_http_502_perc",
    title=Title("Percentage of HTTP 502 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_aws_http_503_perc = metrics.Metric(
    name="aws_http_503_perc",
    title=Title("Percentage of HTTP 503 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_ORANGE,
)

metric_aws_http_504_perc = metrics.Metric(
    name="aws_http_504_perc",
    title=Title("Percentage of HTTP 504 errors"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_http_50x_errors_perc = graphs.Graph(
    name="aws_http_50x_errors_perc",
    title=Title("Percentage of HTTP 500/2/3/4 Errors"),
    compound_lines=[
        "aws_http_500_perc",
        "aws_http_502_perc",
        "aws_http_503_perc",
        "aws_http_504_perc",
    ],
)
