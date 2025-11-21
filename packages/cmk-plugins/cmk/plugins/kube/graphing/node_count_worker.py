#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_node_count_worker_total = metrics.Metric(
    name="kube_node_count_worker_total",
    title=Title("Worker nodes total"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_node_count_worker_ready = metrics.Metric(
    name="kube_node_count_worker_ready",
    title=Title("Worker nodes ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_count_worker_not_ready = metrics.Metric(
    name="kube_node_count_worker_not_ready",
    title=Title("Worker nodes not ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_kube_node_count_worker = graphs.Graph(
    name="kube_node_count_worker",
    title=Title("Worker nodes"),
    compound_lines=[
        "kube_node_count_worker_ready",
        "kube_node_count_worker_not_ready",
    ],
    simple_lines=["kube_node_count_worker_total"],
)
