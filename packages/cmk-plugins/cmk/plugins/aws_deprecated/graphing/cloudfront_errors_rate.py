#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_aws_cloudfront_total_error_rate = metrics.Metric(
    name="aws_cloudfront_total_error_rate",
    title=Title("Total error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_aws_cloudfront_4xx_error_rate = metrics.Metric(
    name="aws_cloudfront_4xx_error_rate",
    title=Title("4xx error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_cloudfront_5xx_error_rate = metrics.Metric(
    name="aws_cloudfront_5xx_error_rate",
    title=Title("5xx error rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

graph_aws_cloudfront_errors_rate = graphs.Graph(
    name="aws_cloudfront_errors_rate",
    title=Title("Error rates"),
    compound_lines=[
        "aws_cloudfront_total_error_rate",
        "aws_cloudfront_4xx_error_rate",
        "aws_cloudfront_5xx_error_rate",
    ],
)
