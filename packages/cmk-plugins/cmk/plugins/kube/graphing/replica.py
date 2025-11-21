#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_desired_replicas = metrics.Metric(
    name="kube_desired_replicas",
    title=Title("Desired replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_updated_replicas = metrics.Metric(
    name="kube_updated_replicas",
    title=Title("Up-to-date replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_ready_replicas = metrics.Metric(
    name="kube_ready_replicas",
    title=Title("Ready replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_available_replicas = metrics.Metric(
    name="kube_available_replicas",
    title=Title("Available replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_kube_replica_available_state = graphs.Graph(
    name="kube_replica_available_state",
    title=Title("Replica available state"),
    compound_lines=["kube_available_replicas"],
    simple_lines=["kube_desired_replicas"],
    optional=["kube_available_replicas"],
)
graph_kube_replica_state = graphs.Graph(
    name="kube_replica_state",
    title=Title("Replica ready state"),
    compound_lines=["kube_ready_replicas"],
    simple_lines=["kube_desired_replicas"],
)
graph_kube_replica_update_state = graphs.Graph(
    name="kube_replica_update_state",
    title=Title("Replica update state"),
    compound_lines=["kube_updated_replicas"],
    simple_lines=["kube_desired_replicas"],
)
