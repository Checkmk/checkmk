#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_free_dhcp_leases = metrics.Metric(
    name="free_dhcp_leases",
    title=Title("Free DHCP leases"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)

perfometer_free_dhcp_leases = perfometers.Perfometer(
    name="free_dhcp_leases",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "free_dhcp_leases",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["free_dhcp_leases"],
)
