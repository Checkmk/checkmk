#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - Usage

This module contains the usage percentages across various memory modules.
They are brought into this module, because we aren't currently allowed
to include them in the other files with the corresponding graphs,
because they aren't part of the graph.
They are not part of the graph, because this currently isn't possible.
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

PERCENT_UNIT = Unit(DecimalNotation("%"), StrictPrecision(2))


metric_jenkins_memory_vm_memory_non_heap_usage = Metric(
    name="jenkins_memory_vm_memory_non_heap_usage",
    title=Title("JVM memory: non-heap: usage"),
    unit=PERCENT_UNIT,
    color=Color.PURPLE,
)

metric_jenkins_memory_vm_memory_heap_usage = Metric(
    name="jenkins_memory_vm_memory_heap_usage",
    title=Title("JVM memory: heap: usage"),
    unit=PERCENT_UNIT,
    color=Color.BLUE,
)

metric_jenkins_memory_vm_memory_pools_g1_old_gen_usage = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_usage",
    title=Title("JVM memory pool G1 Old Gen: usage"),
    unit=PERCENT_UNIT,
    color=Color.ORANGE,
)


metric_jenkins_memory_vm_memory_pools_g1_survivor_space_usage = Metric(
    name="jenkins_memory_vm_memory_pools_g1_survivor_space_usage",
    title=Title("JVM memory pool G1 Survivor Space: usage"),
    unit=PERCENT_UNIT,
    color=Color.PINK,
)

metric_jenkins_memory_vm_memory_pools_g1_old_gen_usage = Metric(
    name="jenkins_memory_vm_memory_pools_g1_old_gen_usage",
    title=Title("JVM memory pool G1 Old Gen: usage"),
    unit=PERCENT_UNIT,
    color=Color.ORANGE,
)

metric_jenkins_memory_vm_memory_pools_g1_eden_space_usage = Metric(
    name="jenkins_memory_vm_memory_pools_g1_eden_space_usage",
    title=Title("JVM memory pool G1 Eden Space: usage"),
    unit=PERCENT_UNIT,
    color=Color.YELLOW,
)

metric_jenkins_memory_vm_memory_pools_metaspace_usage = Metric(
    name="jenkins_memory_vm_memory_pools_metaspace_usage",
    title=Title("JVM memory pool Metaspace: usage"),
    unit=PERCENT_UNIT,
    color=Color.PINK,
)
