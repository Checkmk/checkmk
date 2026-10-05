#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_bytes_accepted = metrics.Metric(
    name="bytes_accepted",
    title=Title("Bytes accepted"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_bytes_dropped = metrics.Metric(
    name="bytes_dropped",
    title=Title("Bytes dropped"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_bytes_rejected = metrics.Metric(
    name="bytes_rejected",
    title=Title("Bytes rejected"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_packets = metrics.Metric(
    name="packets",
    title=Title("Total number of packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_packets_accepted = metrics.Metric(
    name="packets_accepted",
    title=Title("Packets accepted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_packets_dropped = metrics.Metric(
    name="packets_dropped",
    title=Title("Packets dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_packets_rejected = metrics.Metric(
    name="packets_rejected",
    title=Title("Packets rejected"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
