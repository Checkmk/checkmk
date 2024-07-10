#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

EXECUTOR_UNIT = Unit(DecimalNotation("executors"), StrictPrecision(0))

metric_jenkins_num_executors = Metric(
    name="jenkins_num_executors",
    title=Title("Total number of executors"),
    unit=EXECUTOR_UNIT,
    color=Color.WHITE,
)
metric_jenkins_busy_executors = Metric(
    name="jenkins_busy_executors",
    title=Title("Number of busy executors"),
    unit=EXECUTOR_UNIT,
    color=Color.YELLOW,
)
metric_jenkins_idle_executors = Metric(
    name="jenkins_idle_executors",
    title=Title("Number of idle executors"),
    unit=EXECUTOR_UNIT,
    color=Color.GREEN,
)

graph_jenkins_number_of_executors = Graph(
    name="number_of_executors",
    title=Title("Executors"),
    simple_lines=("jenkins_num_executors",),
    compound_lines=(
        "jenkins_busy_executors",
        "jenkins_idle_executors",
    ),
)
