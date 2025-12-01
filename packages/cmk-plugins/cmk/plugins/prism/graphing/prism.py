#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_pd_exclusivesnapshot = metrics.Metric(
    name="pd_exclusivesnapshot",
    title=Title("Usage"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_pd_bandwidth_tx = metrics.Metric(
    name="pd_bandwidth_tx",
    title=Title("Tx"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pd_bandwidth_rx = metrics.Metric(
    name="pd_bandwidth_rx",
    title=Title("Rx"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PURPLE,
)
metric_prism_cluster_mem_used = metrics.Metric(
    name="prism_cluster_mem_used",
    title=Title("Used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_prism_cluster_iobw = metrics.Metric(
    name="prism_cluster_iobw",
    title=Title("IO Bandwith"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_prism_cluster_iops = metrics.Metric(
    name="prism_cluster_iops",
    title=Title("IOPS"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)
metric_prism_cluster_iolatency = metrics.Metric(
    name="prism_cluster_iolatency",
    title=Title("Latency"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
