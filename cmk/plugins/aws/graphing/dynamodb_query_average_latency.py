#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())

metric_aws_dynamodb_query_average_latency = metrics.Metric(
    name="aws_dynamodb_query_average_latency",
    title=Title("Average latency of successful query requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_dynamodb_query_maximum_latency = metrics.Metric(
    name="aws_dynamodb_query_maximum_latency",
    title=Title("Maximum latency of successful query requests"),
    unit=UNIT_SECOND,
    color=metrics.Color.ORANGE,
)

graph_aws_dynamodb_query_latency = graphs.Graph(
    name="aws_dynamodb_query_latency",
    title=Title("Latency of Query requests"),
    simple_lines=[
        "aws_dynamodb_query_average_latency",
        "aws_dynamodb_query_maximum_latency",
    ],
)
