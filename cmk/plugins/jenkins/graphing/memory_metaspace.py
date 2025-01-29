#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: memory - Metaspace
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

MEMORY_UNIT = Unit(IECNotation("B"), StrictPrecision(2))

metric_jenkins_memory_vm_memory_pools_metaspace_init = Metric(
    name="jenkins_memory_vm_memory_pools_metaspace_init",
    title=Title("JVM memory pool Metaspace: initially requested"),
    unit=MEMORY_UNIT,
    color=Color.DARK_PINK,
)
metric_jenkins_memory_vm_memory_pools_metaspace_committed = Metric(
    name="jenkins_memory_vm_memory_pools_metaspace_committed",
    title=Title("JVM memory pool Metaspace: available by OS"),
    unit=MEMORY_UNIT,
    color=Color.DARK_YELLOW,
)
metric_jenkins_memory_vm_memory_pools_metaspace_used = Metric(
    name="jenkins_memory_vm_memory_pools_metaspace_used",
    title=Title("JVM memory pool Metaspace: used"),
    unit=MEMORY_UNIT,
    color=Color.PINK,
)
metric_jenkins_memory_vm_memory_pools_metaspace_max = Metric(
    name="jenkins_memory_vm_memory_pools_metaspace_max",
    title=Title("JVM memory pool Metaspace: max. allowed"),
    unit=MEMORY_UNIT,
    color=Color.LIGHT_PINK,
)

graph_jenkins_memory_pools_metaspace = Graph(
    name="jenkins_memory_pools_metaspace",
    title=Title("Jenkins memory pool Metaspace"),
    simple_lines=(
        "jenkins_memory_vm_memory_pools_metaspace_committed",
        "jenkins_memory_vm_memory_pools_metaspace_used",
        "jenkins_memory_vm_memory_pools_metaspace_init",
        "jenkins_memory_vm_memory_pools_metaspace_max",
    ),
    optional=("jenkins_memory_vm_memory_pools_metaspace_max",),
)
