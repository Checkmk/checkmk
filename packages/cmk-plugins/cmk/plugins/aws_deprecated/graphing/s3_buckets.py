#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_s3_buckets = metrics.Metric(
    name="aws_s3_buckets",
    title=Title("Buckets"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

perfometer_aws_s3_buckets = perfometers.Perfometer(
    name="aws_s3_buckets",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(90)),
    segments=["aws_s3_buckets"],
)

graph_buckets = graphs.Graph(
    name="buckets",
    title=Title("Buckets"),
    simple_lines=["aws_s3_buckets"],
)
