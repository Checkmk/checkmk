#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_high_wat = metrics.Metric(
    name="mem_high_wat",
    title=Title("High watermark"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_low_wat = metrics.Metric(
    name="mem_low_wat",
    title=Title("Low watermark"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_memused_couchbase_bucket = metrics.Metric(
    name="memused_couchbase_bucket",
    title=Title("Memory used"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)

graph_couchbase_bucket_memory = graphs.Graph(
    name="couchbase_bucket_memory",
    title=Title("Bucket memory"),
    compound_lines=["memused_couchbase_bucket"],
    simple_lines=[
        "mem_low_wat",
        "mem_high_wat",
    ],
)
