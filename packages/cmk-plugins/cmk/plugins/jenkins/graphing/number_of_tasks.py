#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

TASKS_UNIT = Unit(DecimalNotation("tasks"), StrictPrecision(0))

metric_jenkins_stuck_tasks = Metric(
    name="jenkins_stuck_tasks",
    title=Title("Number of stuck tasks"),
    unit=TASKS_UNIT,
    color=Color.RED,
)

metric_jenkins_blocked_tasks = Metric(
    name="jenkins_blocked_tasks",
    title=Title("Number of blocked tasks"),
    unit=TASKS_UNIT,
    color=Color.YELLOW,
)

metric_jenkins_pending_tasks = Metric(
    name="jenkins_pending_tasks",
    title=Title("Number of pending tasks"),
    unit=TASKS_UNIT,
    color=Color.GREEN,
)

# States for jobs in the Jenkins queue are taken from
# https://github.com/jenkinsci/jenkins/blob/master/core/src/main/java/hudson/model/Queue.java
# State meanings:
# pending: item waiting for an executor
# blocked: another build is in progress, required resources are not available or otherwise blocked
# stuck: item is starving for an executor for too long.
graph_jenkins_number_of_tasks = Graph(
    name="number_of_tasks",
    title=Title("Tasks"),
    compound_lines=(
        "jenkins_pending_tasks",
        "jenkins_blocked_tasks",
        "jenkins_stuck_tasks",
    ),
)
