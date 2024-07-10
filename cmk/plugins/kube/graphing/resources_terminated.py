#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_pod_succeeded = metrics.Metric(
    name="kube_pod_succeeded",
    title=Title("Succeeded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_pod_failed = metrics.Metric(
    name="kube_pod_failed",
    title=Title("Failed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_kube_resources_terminated = graphs.Graph(
    name="kube_resources_terminated",
    title=Title("Terminated pod resources"),
    simple_lines=[
        "kube_pod_succeeded",
        "kube_pod_failed",
    ],
)
