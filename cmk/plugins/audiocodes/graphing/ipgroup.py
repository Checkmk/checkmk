#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("1/s"))
UNIT_SECOND = metrics.Unit(metrics.TimeNotation())


metric_audiocodes_active_calls_in = metrics.Metric(
    name="audiocodes_ipgroup_active_calls_in",
    title=Title("IP group active calls in"),
    unit=UNIT_COUNT,
    color=metrics.Color.GREEN,
)

metric_audiocodes_active_calls_out = metrics.Metric(
    name="audiocodes_ipgroup_active_calls_out",
    title=Title("IP group active calls out"),
    unit=UNIT_COUNT,
    color=metrics.Color.LIGHT_GREEN,
)

graph_audiocodes_ipgroup_calls_in_out = graphs.Bidirectional(
    name="audiocodes_ipgroup_calls_in_out",
    title=Title("IP group calls in/out"),
    lower=graphs.Graph(
        name="audiocodes_ipgroup_calls_out",
        title=Title("IP group calls out"),
        compound_lines=[
            "audiocodes_ipgroup_active_calls_out",
        ],
    ),
    upper=graphs.Graph(
        name="audiocodes_ipgroup_calls_in",
        title=Title("IP group calls in"),
        compound_lines=[
            "audiocodes_ipgroup_active_calls_in",
        ],
    ),
)

perfometer_audiocodes_ipgroup_calls_in_out = perfometers.Bidirectional(
    name="audiocodes_ipgroup_calls_in_out",
    right=perfometers.Perfometer(
        name="audiocodes_ipgroup_active_calls_out",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
        segments=["audiocodes_ipgroup_active_calls_out"],
    ),
    left=perfometers.Perfometer(
        name="audiocodes_ipgroup_active_calls_in",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
        segments=["audiocodes_ipgroup_active_calls_in"],
    ),
)
