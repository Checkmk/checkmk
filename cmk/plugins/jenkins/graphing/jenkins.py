#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    AutoPrecision,
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    TimeNotation,
    Unit,
)

# .
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

EXECUTOR_UNIT = Unit(DecimalNotation("executors"), StrictPrecision(0))
TASKS_UNIT = Unit(DecimalNotation("tasks"), StrictPrecision(0))
TIME_SINCE_BUILD_UNIT = Unit(TimeNotation(), AutoPrecision(0))

metric_jenkins_job_score = Metric(
    name="jenkins_job_score",
    title=Title("Job score"),
    unit=Unit(
        DecimalNotation("%"),
        StrictPrecision(0),
    ),
    color=Color.PURPLE,
)

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

metric_jenkins_build_duration = Metric(
    name="jenkins_build_duration",
    title=Title("Build duration"),
    unit=Unit(TimeNotation()),
    color=Color.GREEN,
)

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

metric_jenkins_clock = Metric(
    name="jenkins_clock",
    title=Title("Clock difference"),
    unit=Unit(TimeNotation()),
    color=Color.LIGHT_BLUE,
)

metric_jenkins_temp = Metric(
    name="jenkins_temp",
    title=Title("Available temp space"),
    unit=Unit(IECNotation("B"), StrictPrecision(2)),
    color=Color.LIGHT_GRAY,
)

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

metric_jenkins_queue_length = Metric(
    name="queue",
    title=Title("Queue length"),
    unit=TASKS_UNIT,
    color=Color.CYAN,
)

# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'

graph_jenkins_time_since_build = Graph(
    name="time_since_build",
    title=Title("Time since last builds"),
    simple_lines=("jenkins_last_build", "jenkins_time_since"),
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
