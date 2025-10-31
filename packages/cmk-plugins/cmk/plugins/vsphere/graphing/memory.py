#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

# Consumed Host memory usage is defined as the amount of host memory that is allocated to the
# virtual machine
metric_mem_esx_host = metrics.Metric(
    name="mem_esx_host",
    title=Title("Consumed host memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_mem_esx_host = perfometers.Perfometer(
    name="mem_esx_host",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000000000)),
    segments=["mem_esx_host"],
)
