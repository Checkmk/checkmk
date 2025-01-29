#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_RCU = metrics.Unit(metrics.DecimalNotation("RCU"))

metric_aws_dynamodb_minimum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_minimum_consumed_rcu",
    title=Title("Minimum single-request consumption"),
    unit=UNIT_RCU,
    color=metrics.Color.LIGHT_GREEN,
)

metric_aws_dynamodb_maximum_consumed_rcu = metrics.Metric(
    name="aws_dynamodb_maximum_consumed_rcu",
    title=Title("Maximum single-request consumption"),
    unit=UNIT_RCU,
    color=metrics.Color.ORANGE,
)

graph_aws_dynamodb_read_capacity_single = graphs.Graph(
    name="aws_dynamodb_read_capacity_single",
    title=Title("Single-request consumption"),
    simple_lines=[
        "aws_dynamodb_minimum_consumed_rcu",
        "aws_dynamodb_maximum_consumed_rcu",
    ],
)
