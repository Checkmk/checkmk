#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - G1 Old Gen
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

MEMORY_UNIT = Unit(IECNotation("B"), StrictPrecision(2))


metric_jenkins_memory_vm_memory_pools_g1_old_gen_init = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_init",
    title=Title("JVM memory pool G1 Old Gen: initially requested"),
    unit=MEMORY_UNIT,
    color=Color.DARK_ORANGE,
)
metric_jenkins_memory_vm_memory_pools_g1_old_gen_committed = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_committed",
    title=Title("JVM memory pool G1 Old Gen: available by OS"),
    unit=MEMORY_UNIT,
    color=Color.GREEN,
)
metric_jenkins_memory_vm_memory_pools_g1_old_gen_used = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_used",
    title=Title("JVM memory pool G1 Old Gen: used"),
    unit=MEMORY_UNIT,
    color=Color.LIGHT_ORANGE,
)
metric_jenkins_memory_vm_memory_pools_g1_old_gen_used_after_gc = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_used_after_gc",
    title=Title("JVM memory pool G1 Old Gen: used after GC"),
    unit=MEMORY_UNIT,
    color=Color.ORANGE,
)
metric_jenkins_memory_vm_memory_pools_g1_old_gen_max = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_max",
    title=Title("JVM memory pool G1 Old Gen: max. allowed"),
    unit=MEMORY_UNIT,
    color=Color.DARK_GREEN,
)

graph_jenkins_memory_pools_g1_old_gen = Graph(
    name="jenkins_memory_pools_g1_old_gen",
    title=Title("Jenkins memory pool G1 Old Gen"),
    simple_lines=(
        "jenkins_memory_vm_memory_pools_g1_old_gen_committed",
        "jenkins_memory_vm_memory_pools_g1_old_gen_used",
        "jenkins_memory_vm_memory_pools_g1_old_gen_init",
        "jenkins_memory_vm_memory_pools_g1_old_gen_used_after_gc",
        "jenkins_memory_vm_memory_pools_g1_old_gen_max",
    ),
    optional=("jenkins_memory_vm_memory_pools_g1_old_gen_max",),
)
