#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-04
# File  : cisco_meraki_device_status.py (metrics)
#
# 2023-11-12: added wireless device status (channel, channel width, signal power)
# 2023-12-03: rewriten for garaphing api v1

from cmk.graphing.v1 import Color, graph, Localizable, metric, perfometer, Unit

metric_meraki_last_reported = metric.Metric(
    name="last_reported",
    title=Localizable("Last reported"),
    unit=Unit.SECOND,
    color=Color.LIGHT_GREEN,
)

graph_meraki_device_status = graph.Graph(
    name="meraki_device_status",
    title=Localizable("Cisco Meraki Device Last reported"),
    compound_lines=[
        "last_reported",
        metric.WarningOf("last_reported"),
        metric.CriticalOf("last_reported"),
    ],
    # 'range': (0, 'last_reported:max'),
)

perfometer_meraki_last_reported = perfometer.Perfometer(
    name="meraki_last_reported",
    focus_range=perfometer.FocusRange(
        lower=perfometer.Closed(0), upper=perfometer.Open(7200.0)  # 2 hours
    ),
    segments=["last_reported"],
)
