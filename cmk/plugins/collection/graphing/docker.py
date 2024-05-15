#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_docker_active = metrics.Metric(
    name="docker_active",
    title=Title("Active"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_docker_count = metrics.Metric(
    name="docker_count",
    title=Title("Count"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_docker_all_containers = metrics.Metric(
    name="docker_all_containers",
    title=Title("Number of containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_docker_paused_containers = metrics.Metric(
    name="docker_paused_containers",
    title=Title("Paused containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_docker_running_containers = metrics.Metric(
    name="docker_running_containers",
    title=Title("Running containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_docker_stopped_containers = metrics.Metric(
    name="docker_stopped_containers",
    title=Title("Stopped containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_docker_reclaimable = metrics.Metric(
    name="docker_reclaimable",
    title=Title("Reclaimable"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_docker_size = metrics.Metric(
    name="docker_size",
    title=Title("Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_docker_running_containers_docker_paused_containers_docker_stopped_containers = (
    perfometers.Perfometer(
        name="docker_running_containers_docker_paused_containers_docker_stopped_containers",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed("docker_all_containers"),
        ),
        segments=[
            "docker_running_containers",
            "docker_paused_containers",
            "docker_stopped_containers",
        ],
    )
)
perfometer_docker_size = perfometers.Perfometer(
    name="docker_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000000000),
    ),
    segments=["docker_size"],
)

graph_docker_df_count = graphs.Graph(
    name="docker_df_count",
    title=Title("Number of objects"),
    compound_lines=["docker_count"],
    simple_lines=["docker_active"],
)
graph_docker_containers = graphs.Graph(
    name="docker_containers",
    title=Title("Docker containers"),
    compound_lines=[
        "docker_running_containers",
        "docker_paused_containers",
        "docker_stopped_containers",
    ],
    simple_lines=["docker_all_containers"],
)
graph_docker_df = graphs.Graph(
    name="docker_df",
    title=Title("Disk usage"),
    compound_lines=["docker_size"],
    simple_lines=["docker_reclaimable"],
)
