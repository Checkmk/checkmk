#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_aws_bucket_size = metrics.Metric(
    name="aws_bucket_size",
    title=Title("Bucket size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)

perfometer_aws_bucket_size = perfometers.Perfometer(
    name="aws_bucket_size",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2000000000)),
    segments=["aws_bucket_size"],
)

graph_bucket_size = graphs.Graph(
    name="bucket_size",
    title=Title("Bucket size"),
    simple_lines=["aws_bucket_size"],
)
