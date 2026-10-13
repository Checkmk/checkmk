#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_mail_latency = metrics.Metric(
    name="mail_latency",
    title=Title("Mail latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)

perfometer_mail_latency = perfometers.Perfometer(
    name="mail_latency",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(8),
    ),
    segments=["mail_latency"],
)
