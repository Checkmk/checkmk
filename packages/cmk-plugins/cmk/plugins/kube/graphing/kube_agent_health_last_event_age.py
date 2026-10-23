#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_kube_agent_last_event_age = metrics.Metric(
    name="kube_agent_last_event_age",
    title=Title("Time since last resource event"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.GREEN,
)

graph_kube_agent_last_event_age = graphs.Graph(
    name="kube_agent_last_event_age",
    title=Title("Time since last resource event"),
    simple_lines=["kube_agent_last_event_age"],
)
