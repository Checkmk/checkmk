#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_elasticsearch_count_rate = metrics.Metric(
    name="elasticsearch_count_rate",
    title=Title("Document count growth per minute"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_elasticsearch_size_rate = metrics.Metric(
    name="elasticsearch_size_rate",
    title=Title("Size growth per minute"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_elasticsearch_rate = perfometers.Stacked(
    name="elasticsearch_rate",
    lower=perfometers.Perfometer(
        name="elasticsearch_count_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20),
        ),
        segments=["elasticsearch_count_rate"],
    ),
    upper=perfometers.Perfometer(
        name="elasticsearch_size_rate",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(9000),
        ),
        segments=["elasticsearch_size_rate"],
    ),
)
