#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_node_container_count_running = metrics.Metric(
    name="kube_node_container_count_running",
    title=Title("Running containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_container_count_terminated = metrics.Metric(
    name="kube_node_container_count_terminated",
    title=Title("Terminated containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_node_container_count_total = metrics.Metric(
    name="kube_node_container_count_total",
    title=Title("Total containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_kube_node_container_count_waiting = metrics.Metric(
    name="kube_node_container_count_waiting",
    title=Title("Waiting containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_kube_node_container_count = graphs.Graph(
    name="kube_node_container_count",
    title=Title("Containers"),
    compound_lines=[
        "kube_node_container_count_running",
        "kube_node_container_count_waiting",
        "kube_node_container_count_terminated",
    ],
    simple_lines=[
        "kube_node_container_count_total",
        metrics.WarningOf("kube_node_container_count_total"),
        metrics.CriticalOf("kube_node_container_count_total"),
    ],
)

perfometer_kube_node_container_count_running = perfometers.Perfometer(
    name="kube_node_container_count_running",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        # Rough estimate: Kubernetes' "large cluster" guidelines cap a cluster
        # at 5000 nodes and 300000 containers, which evenly distributed is 60
        # containers/node. Smaller clusters concentrate more containers per
        # node, so we use a higher upper of 250 to keep the linear range useful
        # there.
        # https://kubernetes.io/docs/setup/best-practices/cluster-large/
        perfometers.Open(250),
    ),
    segments=["kube_node_container_count_running"],
)
