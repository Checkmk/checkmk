#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))


metric_total_number = metrics.Metric(
    name="podman_pods_total_number",
    title=Title("Total number of Podman pods"),
    unit=UNIT,
    color=metrics.Color.BLUE,
)

metric_running_number = metrics.Metric(
    name="podman_pods_running_number",
    title=Title("Number of running Podman pods"),
    unit=UNIT,
    color=metrics.Color.DARK_GREEN,
)

metric_dead_number = metrics.Metric(
    name="podman_pods_dead_number",
    title=Title("Number of dead Podman pods"),
    unit=UNIT,
    color=metrics.Color.GRAY,
)

perfometer_running_number = perfometers.Perfometer(
    name="podman_pods_running_number",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(10),
    ),
    segments=["podman_pods_running_number"],
)

graph_podman_pods = graphs.Graph(
    name="podman_pods_total_number",
    title=Title("Podman Pods"),
    simple_lines=["podman_pods_total_number"],
    compound_lines=[
        "podman_pods_dead_number",
        "podman_pods_running_number",
    ],
)
