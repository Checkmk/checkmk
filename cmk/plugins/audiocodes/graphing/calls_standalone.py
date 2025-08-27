#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_SECOND = metrics.Unit(metrics.TimeNotation())


metric_audiocodes_average_call_duration = metrics.Metric(
    name="audiocodes_average_call_duration",
    title=Title("Average call duration"),
    unit=UNIT_SECOND,
    color=metrics.Color.PURPLE,
)

metric_audiocodes_answer_seizure_ratio = metrics.Metric(
    name="audiocodes_answer_seizure_ratio",
    title=Title("Answer seizure ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PINK,
)

metric_audiocodes_network_effectiveness_ratio = metrics.Metric(
    name="audiocodes_network_effectiveness_ratio",
    title=Title("Network effectiveness ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
