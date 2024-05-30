#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: threads
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

THREADS_UNIT = Unit(DecimalNotation(""), StrictPrecision(0))

metric_jenkins_threads_total = Metric(
    name="jenkins_threads_vm_count",
    title=Title("Threads: total"),
    unit=THREADS_UNIT,
    color=Color.WHITE,
)
metric_jenkins_threads_active = Metric(
    name="jenkins_threads_vm_runnable_count",
    title=Title("Threads: active"),
    unit=THREADS_UNIT,
    color=Color.GREEN,
)
metric_jenkins_threads_blocked = Metric(
    name="jenkins_threads_vm_blocked_count",
    title=Title("Threads: blocked"),
    unit=THREADS_UNIT,
    color=Color.YELLOW,
)
metric_jenkins_threads_daemons = Metric(
    name="jenkins_threads_vm_daemon_count",
    title=Title("Threads: daemon"),
    unit=THREADS_UNIT,
    color=Color.CYAN,
)
metric_jenkins_threads_deadlocked = Metric(
    name="jenkins_threads_vm_deadlock_count",
    title=Title("Threads: deadlocked"),
    unit=THREADS_UNIT,
    color=Color.RED,
)
metric_jenkins_threads_unstarted = Metric(
    name="jenkins_threads_vm_new_count",
    title=Title("Threads: unstarted"),
    unit=THREADS_UNIT,
    color=Color.LIGHT_GREEN,
)
metric_jenkins_threads_terminated = Metric(
    name="jenkins_threads_vm_terminated_count",
    title=Title("Threads: terminated"),
    unit=THREADS_UNIT,
    color=Color.DARK_GRAY,
)
metric_jenkins_threads_waiting = Metric(
    name="jenkins_threads_vm_waiting_count",
    title=Title("Threads: waiting"),
    unit=THREADS_UNIT,
    color=Color.PINK,
)
metric_jenkins_threads_timed_waiting = Metric(
    name="jenkins_threads_vm_timed_waiting_count",
    title=Title("Threads: timed waiting"),
    unit=THREADS_UNIT,
    color=Color.LIGHT_PINK,
)

# Daemon and deadlocked threads do not count towards the total.
# Daemon threads can be waiting, being blocked, etc.
graph_jenkins_threads = Graph(
    name="jenkins_threads",
    title=Title("Threads"),
    simple_lines=(
        "jenkins_threads_vm_deadlock_count",
        "jenkins_threads_vm_daemon_count",
        "jenkins_threads_vm_count",
    ),
    compound_lines=(
        "jenkins_threads_vm_terminated_count",
        "jenkins_threads_vm_runnable_count",
        "jenkins_threads_vm_new_count",
        "jenkins_threads_vm_timed_waiting_count",
        "jenkins_threads_vm_waiting_count",
        "jenkins_threads_vm_blocked_count",
    ),
)
