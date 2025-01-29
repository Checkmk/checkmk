#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_kernel_stack = metrics.Metric(
    name="mem_lnx_kernel_stack",
    title=Title("Kernel stack"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_mem_lnx_mlocked = metrics.Metric(
    name="mem_lnx_mlocked",
    title=Title("Locked mmap() data"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_page_tables = metrics.Metric(
    name="mem_lnx_page_tables",
    title=Title("Page tables"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_memory_that_cannot_be_swapped_out = graphs.Graph(
    name="memory_that_cannot_be_swapped_out",
    title=Title("Memory that cannot be swapped out"),
    compound_lines=[
        "mem_lnx_kernel_stack",
        "mem_lnx_page_tables",
        "mem_lnx_mlocked",
    ],
)
