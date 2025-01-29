#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_notification_delivery_rate = metrics.Metric(
    name="notification_delivery_rate",
    title=Title("Notification delivery rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)

perfometer_notification_delivery_rate = perfometers.Perfometer(
    name="notification_delivery_rate",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["notification_delivery_rate"],
)
