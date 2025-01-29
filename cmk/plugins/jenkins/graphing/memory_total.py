#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - total memory
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

MEMORY_UNIT = Unit(IECNotation("B"), StrictPrecision(2))


metric_jenkins_memory_vm_memory_total_init = Metric(
    name="jenkins_memory_vm_memory_total_init",
    title=Title("JVM memory total: initially requested"),
    unit=MEMORY_UNIT,
    color=Color.DARK_CYAN,
)
metric_jenkins_memory_vm_memory_total_used = Metric(
    name="jenkins_memory_vm_memory_total_used",
    title=Title("JVM memory total: used"),
    unit=MEMORY_UNIT,
    color=Color.PURPLE,
)
metric_jenkins_memory_vm_memory_total_committed = Metric(
    name="jenkins_memory_vm_memory_total_committed",
    title=Title("JVM memory total: available by OS"),
    unit=MEMORY_UNIT,
    color=Color.LIGHT_CYAN,
)
metric_jenkins_memory_vm_memory_total_max = Metric(
    name="jenkins_memory_vm_memory_total_max",
    title=Title("JVM memory total: max. allowed"),
    unit=MEMORY_UNIT,
    color=Color.CYAN,
)

graph_jenkins_memory_vm_memory_total = Graph(
    name="jenkins_memory_vm_memory_total",
    title=Title("JVM total memory"),
    simple_lines=(
        "jenkins_memory_vm_memory_total_init",
        "jenkins_memory_vm_memory_total_used",
        "jenkins_memory_vm_memory_total_committed",
        "jenkins_memory_vm_memory_total_max",
    ),
    optional=("jenkins_memory_vm_memory_total_max",),
)
