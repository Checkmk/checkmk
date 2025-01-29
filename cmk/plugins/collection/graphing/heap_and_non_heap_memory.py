#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_heap = metrics.Metric(
    name="mem_heap",
    title=Title("Heap memory usage"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_heap_committed = metrics.Metric(
    name="mem_heap_committed",
    title=Title("Heap memory committed"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_nonheap = metrics.Metric(
    name="mem_nonheap",
    title=Title("Non-heap memory usage"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_nonheap_committed = metrics.Metric(
    name="mem_nonheap_committed",
    title=Title("Non-heap memory committed"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_mem_heap = perfometers.Perfometer(
    name="mem_heap",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "mem_heap",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["mem_heap"],
)
perfometer_mem_nonheap_mem_heap = perfometers.Stacked(
    name="mem_nonheap_mem_heap",
    lower=perfometers.Perfometer(
        name="mem_nonheap",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(200000000),
        ),
        segments=["mem_nonheap"],
    ),
    upper=perfometers.Perfometer(
        name="mem_heap",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(200000000),
        ),
        segments=["mem_heap"],
    ),
)
perfometer_mem_nonheap = perfometers.Perfometer(
    name="mem_nonheap",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "mem_nonheap",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["mem_nonheap"],
)

graph_heap_and_non_heap_memory = graphs.Graph(
    name="heap_and_non_heap_memory",
    title=Title("Heap and non-heap memory"),
    compound_lines=[
        "mem_heap",
        "mem_nonheap",
    ],
    conflicting=[
        "mem_heap_committed",
        "mem_nonheap_committed",
    ],
)
graph_heap_memory_usage = graphs.Graph(
    name="heap_memory_usage",
    title=Title("Heap memory usage"),
    simple_lines=[
        "mem_heap_committed",
        "mem_heap",
        metrics.WarningOf("mem_heap"),
        metrics.CriticalOf("mem_heap"),
    ],
)
graph_non_heap_memory_usage = graphs.Graph(
    name="non-heap_memory_usage",
    title=Title("Non-heap memory usage"),
    simple_lines=[
        "mem_nonheap_committed",
        "mem_nonheap",
        metrics.WarningOf("mem_nonheap"),
        metrics.CriticalOf("mem_nonheap"),
        metrics.MaximumOf(
            "mem_nonheap",
            metrics.Color.GRAY,
        ),
    ],
)
