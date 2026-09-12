#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_kube_agent_kubelet_stats_scrape_time = metrics.Metric(
    name="kube_agent_kubelet_stats_scrape_time",
    title=Title("Kubelet statistics: scrape duration"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.BLUE,
)

metric_kube_agent_kubelet_health_scrape_time = metrics.Metric(
    name="kube_agent_kubelet_health_scrape_time",
    title=Title("Kubelet health: scrape duration"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.GREEN,
)

metric_kube_agent_system_agent_scrape_time = metrics.Metric(
    name="kube_agent_system_agent_scrape_time",
    title=Title("System agent: scrape duration"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.PURPLE,
)

graph_kube_agent_scrape_time = graphs.Graph(
    name="kube_agent_scrape_time",
    title=Title("Payload scrape duration"),
    simple_lines=[
        "kube_agent_kubelet_stats_scrape_time",
        "kube_agent_kubelet_health_scrape_time",
        "kube_agent_system_agent_scrape_time",
    ],
    optional=[
        "kube_agent_kubelet_stats_scrape_time",
        "kube_agent_kubelet_health_scrape_time",
        "kube_agent_system_agent_scrape_time",
    ],
)
