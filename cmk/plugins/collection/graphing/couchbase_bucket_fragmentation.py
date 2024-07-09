#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

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


graph_couchbase_bucket_fragmentation = graphs.Graph(
    name="couchbase_bucket_fragmentation",
    title=Title("Fragmentation"),
    compound_lines=[
        "docs_fragmentation",
        "views_fragmentation",
    ],
)
