#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_AMPERE = metrics.Unit(metrics.DecimalNotation("A"), metrics.AutoPrecision(3))
UNIT_ELECTRICAL_APPARENT_POWER = metrics.Unit(
    metrics.DecimalNotation("VA"), metrics.AutoPrecision(3)
)
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_differential_current_ac = metrics.Metric(
    name="differential_current_ac",
    title=Title("Differential current AC"),
    unit=UNIT_AMPERE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_differential_current_dc = metrics.Metric(
    name="differential_current_dc",
    title=Title("Differential current DC"),
    unit=UNIT_AMPERE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_appower = metrics.Metric(
    name="appower",
    title=Title("Electrical apparent power"),
    unit=UNIT_ELECTRICAL_APPARENT_POWER,
    color=metrics.Color.DARK_YELLOW,
)
metric_trend_hoursleft = metrics.Metric(
    name="trend_hoursleft",
    title=Title("Time left until full"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_outqlen = metrics.Metric(
    name="outqlen",
    title=Title("Length of output queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_predict_load15 = metrics.Metric(
    name="predict_load15",
    title=Title("Predicted average for 15 minute CPU load"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)
metric_age_youngest = metrics.Metric(
    name="age_youngest",
    title=Title("Youngest age"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_process_handles = metrics.Metric(
    name="process_handles",
    title=Title("Process handles"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
