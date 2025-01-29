#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_cpu_credits_consumed = metrics.Metric(
    name="cpu_credits_consumed",
    title=Title("Credits consumed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_cpu_credits_remaining = metrics.Metric(
    name="cpu_credits_remaining",
    title=Title("Credits remaining"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

graph_cpu_credits = graphs.Graph(
    name="cpu_credits",
    title=Title("CPU credits"),
    simple_lines=[
        "cpu_credits_consumed",
        "cpu_credits_remaining",
    ],
)
