#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_kube_memory_allocatable = metrics.Metric(
    name="kube_memory_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_kube_memory_limit = metrics.Metric(
    name="kube_memory_limit",
    title=Title("Limits"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_kube_memory_request = metrics.Metric(
    name="kube_memory_request",
    title=Title("Requests"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_kube_memory_usage = metrics.Metric(
    name="kube_memory_usage",
    title=Title("Usage"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)

perfometer_kube_memory_usage = perfometers.Perfometer(
    name="kube_memory_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1000000000),
    ),
    segments=["kube_memory_usage"],
)

graph_kube_memory_usage = graphs.Graph(
    name="kube_memory_usage",
    title=Title("Memory"),
    compound_lines=["kube_memory_usage"],
    simple_lines=[
        "kube_memory_request",
        "kube_memory_limit",
        "kube_memory_allocatable",
        metrics.WarningOf("kube_memory_usage"),
        metrics.CriticalOf("kube_memory_usage"),
    ],
    optional=[
        "kube_memory_request",
        "kube_memory_limit",
        "kube_memory_usage",
        "kube_memory_allocatable",
    ],
)
