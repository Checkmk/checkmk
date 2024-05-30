#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - non-heap
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

MEMORY_UNIT = Unit(IECNotation("B"), StrictPrecision(2))

metric_jenkins_memory_vm_memory_non_heap_init = Metric(
    name="jenkins_memory_vm_memory_non_heap_init",
    title=Title("JVM memory: non-heap: initially requested"),
    unit=MEMORY_UNIT,
    color=Color.DARK_PURPLE,
)
metric_jenkins_memory_vm_memory_non_heap_used = Metric(
    name="jenkins_memory_vm_memory_non_heap_used",
    title=Title("JVM memory: non-heap: used"),
    unit=MEMORY_UNIT,
    color=Color.CYAN,
)
metric_jenkins_memory_vm_memory_non_heap_committed = Metric(
    name="jenkins_memory_vm_memory_non_heap_committed",
    title=Title("JVM memory: non-heap: available by OS"),
    unit=MEMORY_UNIT,
    color=Color.LIGHT_PURPLE,
)
metric_jenkins_memory_vm_memory_non_heap_max = Metric(
    name="jenkins_memory_vm_memory_non_heap_max",
    title=Title("JVM memory: non-heap: max. allowed"),
    unit=MEMORY_UNIT,
    color=Color.PURPLE,
)

graph_jenkins_memory_vm_memory_non_heap = Graph(
    name="jenkins_memory_vm_memory_non_heap",
    title=Title("JVM memory: non-heap"),
    simple_lines=(
        "jenkins_memory_vm_memory_non_heap_init",
        "jenkins_memory_vm_memory_non_heap_used",
        "jenkins_memory_vm_memory_non_heap_committed",
        "jenkins_memory_vm_memory_non_heap_max",
    ),
    optional=("jenkins_memory_vm_memory_non_heap_max",),
)
