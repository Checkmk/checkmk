#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_deviation_airflow = metrics.Metric(
    name="deviation_airflow",
    title=Title("Airflow deviation"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

perfometer_deviation_airflow = perfometers.Perfometer(
    name="deviation_airflow",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(10),
    ),
    segments=["deviation_airflow"],
)
