#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))


metric_audiocodes_active_calls_in = metrics.Metric(
    name="audiocodes_active_calls_in",
    title=Title("Active Calls In"),
    unit=UNIT_COUNT,
    color=metrics.Color.GREEN,
)

metric_audiocodes_active_calls_out = metrics.Metric(
    name="audiocodes_active_calls_out",
    title=Title("Active Calls Out"),
    unit=UNIT_COUNT,
    color=metrics.Color.LIGHT_GREEN,
)

graph_audiocodes_calls_in_out = graphs.Bidirectional(
    name="audiocodes_calls_in_out",
    title=Title("Calls In/Out"),
    lower=graphs.Graph(
        name="audiocodes_calls_out",
        title=Title("Calls Out"),
        compound_lines=[
            "audiocodes_active_calls_out",
        ],
    ),
    upper=graphs.Graph(
        name="audiocodes_calls_in",
        title=Title("Calls In"),
        compound_lines=[
            "audiocodes_active_calls_in",
        ],
    ),
)

perfometer_audiocodes_calls_in_out = perfometers.Bidirectional(
    name="audiocodes_calls_in_out",
    right=perfometers.Perfometer(
        name="audiocodes_active_calls_out",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
        segments=["audiocodes_active_calls_out"],
    ),
    left=perfometers.Perfometer(
        name="audiocodes_active_calls_in",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
        segments=["audiocodes_active_calls_in"],
    ),
)
