#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

# # Active Guest Memory is defined as the amount of guest memory that is currently being used by the
# guest operating system and its applications
metric_mem_esx_guest = metrics.Metric(
    name="mem_esx_guest",
    title=Title("Active guest memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_mem_esx_ballooned = metrics.Metric(
    name="mem_esx_ballooned",
    title=Title("Ballooned memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
