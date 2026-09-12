#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_kube_agent_kubelet_stats_age = metrics.Metric(
    name="kube_agent_kubelet_stats_age",
    title=Title("Kubelet statistics: time since receipt"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.BLUE,
)

metric_kube_agent_kubelet_health_age = metrics.Metric(
    name="kube_agent_kubelet_health_age",
    title=Title("Kubelet health: time since receipt"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.GREEN,
)

metric_kube_agent_system_agent_age = metrics.Metric(
    name="kube_agent_system_agent_age",
    title=Title("System agent: time since receipt"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.PURPLE,
)

graph_kube_agent_payload_age = graphs.Graph(
    name="kube_agent_payload_age",
    title=Title("Time since payload receipt"),
    simple_lines=[
        "kube_agent_kubelet_stats_age",
        "kube_agent_kubelet_health_age",
        "kube_agent_system_agent_age",
    ],
    optional=[
        "kube_agent_kubelet_stats_age",
        "kube_agent_kubelet_health_age",
        "kube_agent_system_agent_age",
    ],
)
