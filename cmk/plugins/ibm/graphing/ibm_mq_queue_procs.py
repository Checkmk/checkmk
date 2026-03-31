#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_ipprocs = metrics.Metric(
    name="ipprocs",
    title=Title("Open input handles"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_opprocs = metrics.Metric(
    name="opprocs",
    title=Title("Open output handles"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_ibm_mq_queue_procs = graphs.Graph(
    name="ibm_mq_queue_procs",
    title=Title("Open input/output handles"),
    simple_lines=[
        "ipprocs",
        "opprocs",
    ],
)
