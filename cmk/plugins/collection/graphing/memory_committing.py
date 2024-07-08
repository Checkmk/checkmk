#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_commit_limit = metrics.Metric(
    name="mem_lnx_commit_limit",
    title=Title("Commit limit"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_committed_as = metrics.Metric(
    name="mem_lnx_committed_as",
    title=Title("Committed memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_total_total = metrics.Metric(
    name="mem_lnx_total_total",
    title=Title("Total virtual memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_memory_committing = graphs.Graph(
    name="memory_committing",
    title=Title("Memory committing"),
    compound_lines=[
        "mem_lnx_committed_as",
        "mem_lnx_commit_limit",
    ],
    simple_lines=["mem_lnx_total_total"],
)
