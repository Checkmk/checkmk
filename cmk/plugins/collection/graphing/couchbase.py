#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

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
metric_docs_fragmentation = metrics.Metric(
    name="docs_fragmentation",
    title=Title("Documents fragmentation"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_views_fragmentation = metrics.Metric(
    name="views_fragmentation",
    title=Title("Views fragmentation"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_vbuckets = metrics.Metric(
    name="vbuckets",
    title=Title("vBuckets"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_pending_vbuckets = metrics.Metric(
    name="pending_vbuckets",
    title=Title("Pending vBuckets"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
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
graph_couchbase_bucket_fragmentation = graphs.Graph(
    name="couchbase_bucket_fragmentation",
    title=Title("Fragmentation"),
    compound_lines=[
        "docs_fragmentation",
        "views_fragmentation",
    ],
)
