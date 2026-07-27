#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Graphing for F5OS rSeries CPU checks.
#
# The primary ``util`` metric is defined centrally (cmk.plugins.cpu.graphing) and
# rendered by the shared CPU graph and perf-o-meter, so we only add the platform's
# short- and mid-term averages here.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

_UNIT_PERCENTAGE = Unit(DecimalNotation("%"), StrictPrecision(0))

metric_f5os_util_5sec = Metric(
    name="util_5sec",
    title=Title("CPU utilization (5 sec avg)"),
    unit=_UNIT_PERCENTAGE,
    color=Color.ORANGE,
)

metric_f5os_util_5min = Metric(
    name="util_5min",
    title=Title("CPU utilization (5 min avg)"),
    unit=_UNIT_PERCENTAGE,
    color=Color.YELLOW,
)

graph_f5os_rseries_cpu = Graph(
    name="f5os_rseries_cpu",
    title=Title("F5OS CPU utilization averages"),
    simple_lines=["util_5sec", "util_5min"],
)
