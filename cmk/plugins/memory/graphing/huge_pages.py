#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_huge_pages_free = metrics.Metric(
    name="mem_lnx_huge_pages_free",
    title=Title("Huge pages free"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_mem_lnx_huge_pages_rsvd = metrics.Metric(
    name="mem_lnx_huge_pages_rsvd",
    title=Title("Huge pages reserved part of free"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_huge_pages_surp = metrics.Metric(
    name="mem_lnx_huge_pages_surp",
    title=Title("Huge pages surplus"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_huge_pages_total = metrics.Metric(
    name="mem_lnx_huge_pages_total",
    title=Title("Huge pages total"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_huge_pages = graphs.Graph(
    name="huge_pages",
    title=Title("Huge pages"),
    compound_lines=[
        "mem_lnx_huge_pages_free",
        "mem_lnx_huge_pages_rsvd",
    ],
    simple_lines=[
        "mem_lnx_huge_pages_total",
        "mem_lnx_huge_pages_surp",
    ],
)
