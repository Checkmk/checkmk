#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_vpn_tunnels = metrics.Metric(
    name="active_vpn_tunnels",
    title=Title("Active VPN tunnels"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_active_vpn_tunnels = perfometers.Perfometer(
    name="active_vpn_tunnels",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "active_vpn_tunnels",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["active_vpn_tunnels"],
)
