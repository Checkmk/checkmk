#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_docker_size = metrics.Metric(
    name="docker_size",
    title=Title("Size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_docker_reclaimable = metrics.Metric(
    name="docker_reclaimable",
    title=Title("Reclaimable"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)

perfometer_docker_size = perfometers.Perfometer(
    name="docker_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000000000),
    ),
    segments=["docker_size"],
)

graph_docker_df = graphs.Graph(
    name="docker_df",
    title=Title("Disk usage"),
    compound_lines=["docker_size"],
    simple_lines=["docker_reclaimable"],
)
