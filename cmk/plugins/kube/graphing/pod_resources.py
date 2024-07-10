#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_pod_allocatable = metrics.Metric(
    name="kube_pod_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_kube_pod_free = metrics.Metric(
    name="kube_pod_free",
    title=Title("Free"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_pod_pending = metrics.Metric(
    name="kube_pod_pending",
    title=Title("Pending"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_pod_running = metrics.Metric(
    name="kube_pod_running",
    title=Title("Running"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_kube_pod_resources = graphs.Graph(
    name="kube_pod_resources",
    title=Title("Allocated pod resources"),
    compound_lines=[
        "kube_pod_running",
        "kube_pod_pending",
        "kube_pod_free",
    ],
    simple_lines=["kube_pod_allocatable"],
    optional=[
        "kube_pod_free",
        "kube_pod_allocatable",
    ],
)
