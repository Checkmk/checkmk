#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_consumers = metrics.Metric(
    name="consumers",
    title=Title("Consumers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_exchanges = metrics.Metric(
    name="exchanges",
    title=Title("Exchanges"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_queues = metrics.Metric(
    name="queues",
    title=Title("Queues"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_gc_runs = metrics.Metric(
    name="gc_runs",
    title=Title("GC runs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_gc_runs_rate = metrics.Metric(
    name="gc_runs_rate",
    title=Title("GC runs rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
metric_runtime_run_queue = metrics.Metric(
    name="runtime_run_queue",
    title=Title("Runtime run queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_gc_bytes = metrics.Metric(
    name="gc_bytes",
    title=Title("Bytes reclaimed by GC"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_gc_bytes_rate = metrics.Metric(
    name="gc_bytes_rate",
    title=Title("Bytes reclaimed by GC rate"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_channels = metrics.Metric(
    name="channels",
    title=Title("Channels"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
