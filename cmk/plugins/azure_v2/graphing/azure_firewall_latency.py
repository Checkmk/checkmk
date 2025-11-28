#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())

metric_azure_firewall_latency = metrics.Metric(
    name="azure_firewall_latency",
    title=Title("Azure firewall latency"),
    unit=UNIT_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_azure_firewall_latency = perfometers.Perfometer(
    name="azure_firewall_latency",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(0.002)),
    segments=["azure_firewall_latency"],
)
