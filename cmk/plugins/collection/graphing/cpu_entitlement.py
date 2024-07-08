#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_cpu_entitlement = metrics.Metric(
    name="cpu_entitlement",
    title=Title("Entitlement"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_cpu_entitlement_util = metrics.Metric(
    name="cpu_entitlement_util",
    title=Title("Physical CPU consumption"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

graph_cpu_entitlement = graphs.Graph(
    name="cpu_entitlement",
    title=Title("CPU entitlement"),
    compound_lines=["cpu_entitlement"],
    simple_lines=["cpu_entitlement_util"],
)
