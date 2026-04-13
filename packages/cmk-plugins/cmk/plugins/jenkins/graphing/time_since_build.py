#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import AutoPrecision, Color, Metric, TimeNotation, Unit

TIME_SINCE_BUILD_UNIT = Unit(TimeNotation(), AutoPrecision(0))

metric_jenkins_time_since = Metric(
    name="jenkins_time_since",
    title=Title("Time since last successful build"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.GREEN,
)
metric_jenkins_last_build = Metric(
    name="jenkins_last_build",
    title=Title("Time since last build"),
    unit=TIME_SINCE_BUILD_UNIT,
    color=Color.YELLOW,
)

graph_jenkins_time_since_build = Graph(
    name="time_since_build",
    title=Title("Time since last builds"),
    simple_lines=("jenkins_last_build", "jenkins_time_since"),
)
