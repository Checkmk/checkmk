#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

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
