#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_kube_cpu_usage = metrics.Metric(
    name="kube_cpu_usage",
    title=Title("Usage"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)
metric_kube_cpu_request = metrics.Metric(
    name="kube_cpu_request",
    title=Title("Requests"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_kube_cpu_limit = metrics.Metric(
    name="kube_cpu_limit",
    title=Title("Limits"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_kube_cpu_allocatable = metrics.Metric(
    name="kube_cpu_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

perfometer_kube_cpu_usage = perfometers.Perfometer(
    name="kube_cpu_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["kube_cpu_usage"],
)

graph_kube_cpu_usage = graphs.Graph(
    name="kube_cpu_usage",
    title=Title("CPU"),
    compound_lines=["kube_cpu_usage"],
    simple_lines=[
        "kube_cpu_request",
        "kube_cpu_limit",
        "kube_cpu_allocatable",
        metrics.WarningOf("kube_cpu_usage"),
        metrics.CriticalOf("kube_cpu_usage"),
    ],
    optional=[
        "kube_cpu_request",
        "kube_cpu_limit",
        "kube_cpu_usage",
        "kube_cpu_allocatable",
    ],
)
