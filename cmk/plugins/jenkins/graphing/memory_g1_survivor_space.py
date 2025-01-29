#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - G1 Survivor Space
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

MEMORY_UNIT = Unit(IECNotation("B"), StrictPrecision(2))


metric_jenkins_memory_vm_memory_pools_g1_survivor_space_init = Metric(
    name="jenkins_memory_vm_memory_pools_g1_survivor_space_init",
    title=Title("JVM memory pool G1 Survivor Space: initially requested"),
    unit=MEMORY_UNIT,
    color=Color.DARK_PINK,
)
metric_jenkins_memory_vm_memory_pools_g1_survivor_space_committed = Metric(
    name="jenkins_memory_vm_memory_pools_g1_survivor_space_committed",
    title=Title("JVM memory pool G1 Survivor Space: available by OS"),
    unit=MEMORY_UNIT,
    color=Color.CYAN,
)
metric_jenkins_memory_vm_memory_pools_g1_survivor_space_used = Metric(
    name="jenkins_memory_vm_memory_pools_g1_survivor_space_used",
    title=Title("JVM memory pool G1 Survivor Space: used"),
    unit=MEMORY_UNIT,
    color=Color.LIGHT_PINK,
)
metric_jenkins_memory_vm_memory_pools_g1_survivor_space_used_after_gc = Metric(
    name="jenkins_memory_vm_memory_pools_g1_survivor_space_used_after_gc",
    title=Title("JVM memory pool G1 Survivor Space: used after GC"),
    unit=MEMORY_UNIT,
    color=Color.DARK_CYAN,
)

graph_jenkins_memory_pools_g1_survivor_space = Graph(
    name="jenkins_memory_pools_g1_survivor_space",
    title=Title("Jenkins memory pool G1 Survivor Space"),
    simple_lines=(
        "jenkins_memory_vm_memory_pools_g1_survivor_space_committed",
        "jenkins_memory_vm_memory_pools_g1_survivor_space_used",
        "jenkins_memory_vm_memory_pools_g1_survivor_space_init",
        "jenkins_memory_vm_memory_pools_g1_survivor_space_used_after_gc",
    ),
)
