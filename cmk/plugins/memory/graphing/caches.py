#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_mem_lnx_slab = Metric(
    name="mem_lnx_slab",
    title=Title("Slab (Various smaller caches)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PURPLE,
)
metric_swap_cached = Metric(
    name="swap_cached",
    title=Title("Swap cached"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_GREEN,
)
metric_mem_lnx_cached = Metric(
    name="mem_lnx_cached",
    title=Title("Cached memory"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)
metric_mem_lnx_buffers = Metric(
    name="mem_lnx_buffers",
    title=Title("Buffered memory"),
    unit=UNIT_BYTES,
    color=Color.CYAN,
)

graph_caches = Graph(
    name="caches",
    title=Title("Caches"),
    simple_lines=[
        "mem_lnx_slab",
        "swap_cached",
        "mem_lnx_buffers",
        "mem_lnx_cached",
    ],
)
