#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

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

graph_docker_df_count = graphs.Graph(
    name="docker_df_count",
    title=Title("Number of objects"),
    compound_lines=["docker_count"],
    simple_lines=["docker_active"],
)
