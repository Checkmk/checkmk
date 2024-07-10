#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_kube_pod_restart_count = metrics.Metric(
    name="kube_pod_restart_count",
    title=Title("Restarts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_kube_pod_restart_rate = metrics.Metric(
    name="kube_pod_restart_rate",
    title=Title("Restarts per hour"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

graph_kube_pod_restarts = graphs.Graph(
    name="kube_pod_restarts",
    title=Title("Pod Restarts"),
    simple_lines=[
        "kube_pod_restart_count",
        "kube_pod_restart_rate",
    ],
    optional=["kube_pod_restart_rate"],
)
