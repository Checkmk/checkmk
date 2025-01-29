#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_vmalloc_chunk = metrics.Metric(
    name="mem_lnx_vmalloc_chunk",
    title=Title("Largest free chunk"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_vmalloc_total = metrics.Metric(
    name="mem_lnx_vmalloc_total",
    title=Title("Total address space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_vmalloc_used = metrics.Metric(
    name="mem_lnx_vmalloc_used",
    title=Title("Allocated space"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_vmalloc_address_space_1 = graphs.Graph(
    name="vmalloc_address_space_1",
    title=Title("VMalloc address space"),
    compound_lines=[
        "mem_lnx_vmalloc_used",
        "mem_lnx_vmalloc_chunk",
    ],
    simple_lines=["mem_lnx_vmalloc_total"],
)
# TODO: Why without 'mem_lnx_vmalloc_total'? Should not happen...
graph_vmalloc_address_space_2 = graphs.Graph(
    name="vmalloc_address_space_2",
    title=Title("VMalloc address space"),
    compound_lines=[
        "mem_lnx_vmalloc_used",
        "mem_lnx_vmalloc_chunk",
    ],
)
