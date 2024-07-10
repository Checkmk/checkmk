#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_node_count_control_plane_ready = metrics.Metric(
    name="kube_node_count_control_plane_ready",
    title=Title("Control plane nodes ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_count_control_plane_not_ready = metrics.Metric(
    name="kube_node_count_control_plane_not_ready",
    title=Title("Control plane nodes not ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_node_count_control_plane_total = metrics.Metric(
    name="kube_node_count_control_plane_total",
    title=Title("Control plane nodes total"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

graph_kube_node_count_control_plane = graphs.Graph(
    name="kube_node_count_control_plane",
    title=Title("Control plane nodes"),
    compound_lines=[
        "kube_node_count_control_plane_ready",
        "kube_node_count_control_plane_not_ready",
    ],
    simple_lines=["kube_node_count_control_plane_total"],
)
