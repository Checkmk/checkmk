#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))


metric_total_number = metrics.Metric(
    name="podman_containers_total_number",
    title=Title("Total number of Podman containers"),
    unit=UNIT,
    color=metrics.Color.BLUE,
)

metric_running_number = metrics.Metric(
    name="podman_containers_running_number",
    title=Title("Number of running Podman containers"),
    unit=UNIT,
    color=metrics.Color.DARK_GREEN,
)

metric_created_number = metrics.Metric(
    name="podman_containers_created_number",
    title=Title("Number of created Podman containers"),
    unit=UNIT,
    color=metrics.Color.GREEN,
)

metric_paused_number = metrics.Metric(
    name="podman_containers_paused_number",
    title=Title("Number of paused Podman containers"),
    unit=UNIT,
    color=metrics.Color.DARK_PINK,
)

metric_stopped_number = metrics.Metric(
    name="podman_containers_stopped_number",
    title=Title("Number of stopped Podman containers"),
    unit=UNIT,
    color=metrics.Color.DARK_PURPLE,
)

metric_restarting_number = metrics.Metric(
    name="podman_containers_restarting_number",
    title=Title("Number of restarting Podman containers"),
    unit=UNIT,
    color=metrics.Color.DARK_YELLOW,
)

metric_removing_number = metrics.Metric(
    name="podman_containers_removing_number",
    title=Title("Number of removing Podman containers"),
    unit=UNIT,
    color=metrics.Color.BROWN,
)

metric_dead_number = metrics.Metric(
    name="podman_containers_dead_number",
    title=Title("Number of dead Podman containers"),
    unit=UNIT,
    color=metrics.Color.GRAY,
)

metric_exited_number = metrics.Metric(
    name="podman_containers_exited_number",
    title=Title("Number of exited Podman containers"),
    unit=UNIT,
    color=metrics.Color.CYAN,
)

metric_exited_as_non_zero_number = metrics.Metric(
    name="podman_containers_exited_as_non_zero_number",
    title=Title("Number of exited Podman containers (non-zero)"),
    unit=UNIT,
    color=metrics.Color.DARK_CYAN,
)

perfometer_running_number = perfometers.Perfometer(
    name="podman_containers_running_number",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Closed(
            metrics.MaximumOf(
                "podman_containers_running_number",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["podman_containers_running_number"],
)

graph_podman_containers = graphs.Graph(
    name="podman_containers_total_number",
    title=Title("Podman Containers"),
    simple_lines=["podman_containers_total_number"],
    compound_lines=[
        "podman_containers_exited_as_non_zero_number",
        "podman_containers_exited_number",
        "podman_containers_dead_number",
        "podman_containers_removing_number",
        "podman_containers_restarting_number",
        "podman_containers_stopped_number",
        "podman_containers_paused_number",
        "podman_containers_created_number",
        "podman_containers_running_number",
    ],
)
