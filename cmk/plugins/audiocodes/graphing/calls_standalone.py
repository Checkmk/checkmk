#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_SECOND = metrics.Unit(metrics.TimeNotation())


metric_audiocodes_active_calls = metrics.Metric(
    name="audiocodes_active_calls",
    title=Title("Active Calls"),
    unit=UNIT_COUNT,
    color=metrics.Color.BLUE,
)

metric_audiocodes_calls_per_sec = metrics.Metric(
    name="audiocodes_calls_per_sec",
    title=Title("Calls per Second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)

metric_audiocodes_average_success_ratio = metrics.Metric(
    name="audiocodes_average_success_ratio",
    title=Title("Average Success Ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_audiocodes_average_call_duration = metrics.Metric(
    name="audiocodes_average_call_duration",
    title=Title("Average Call Duration"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)
