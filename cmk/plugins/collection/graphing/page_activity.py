#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_page_reads_sec = metrics.Metric(
    name="page_reads_sec",
    title=Title("Page reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_page_writes_sec = metrics.Metric(
    name="page_writes_sec",
    title=Title("Page writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_page_activity_page_activity = graphs.Bidirectional(
    name="page_activity_page_activity",
    title=Title("Page activity"),
    lower=graphs.Graph(
        name="page_activity",
        title=Title("Page activity"),
        compound_lines=["page_writes_sec"],
    ),
    upper=graphs.Graph(
        name="page_activity",
        title=Title("Page activity"),
        compound_lines=["page_reads_sec"],
    ),
)
