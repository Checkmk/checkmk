#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_qtime_long = metrics.Metric(
    name="qtime_long",
    title=Title("Queue time long"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_qtime_short = metrics.Metric(
    name="qtime_short",
    title=Title("Queue time short"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
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
metric_curdepth = metrics.Metric(
    name="curdepth",
    title=Title("Queue depth"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_msgage = metrics.Metric(
    name="msgage",
    title=Title("Age of oldest message"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_ibm_mq_qtime = graphs.Graph(
    name="ibm_mq_qtime",
    title=Title("Average time messages stay on queue"),
    simple_lines=[
        "qtime_short",
        "qtime_long",
    ],
)
graph_ibm_mq_queue_procs = graphs.Graph(
    name="ibm_mq_queue_procs",
    title=Title("Open input/output handles"),
    simple_lines=[
        "ipprocs",
        "opprocs",
    ],
)
