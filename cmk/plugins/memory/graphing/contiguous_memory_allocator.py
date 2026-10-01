#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"), metrics.StrictPrecision(2))

metric_cma_total = metrics.Metric(
    name="cma_total",
    title=Title("Contiguous memory: Allocated"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_cma_free = metrics.Metric(
    name="cma_free",
    title=Title("Contiguous memory: Free"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BLUE,
)

graph_contiguous_memory_allocator = graphs.Graph(
    name="contiguous_memory_allocator",
    title=Title("Contiguous memory allocator"),
    compound_lines=["cma_free"],
    simple_lines=["cma_total"],
)
