#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_azure_firewall_throughput = metrics.Metric(
    name="azure_firewall_throughput",
    title=Title("Throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)

perfometer_azure_firewall_throughput = perfometers.Perfometer(
    name="azure_firewall_throughput",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2500000000),
    ),
    segments=["azure_firewall_throughput"],
)
