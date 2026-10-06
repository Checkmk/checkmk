#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_num_objects = metrics.Metric(
    name="aws_num_objects",
    title=Title("Number of objects"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

graph_num_objects = graphs.Graph(
    name="num_objects",
    title=Title("Number of bucket objects"),
    simple_lines=["aws_num_objects"],
)
