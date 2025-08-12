#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_SECOND = metrics.Unit(metrics.TimeNotation())


metric_audiocodes_established_calls_in = metrics.Metric(
    name="audiocodes_established_calls_in",
    title=Title("Established calls in rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)

metric_audiocodes_established_calls_out = metrics.Metric(
    name="audiocodes_established_calls_out",
    title=Title("Established calls out rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

graph_audiocodes_established_calls_in_out = graphs.Bidirectional(
    name="audiocodes_established_calls_in_out",
    title=Title("Established calls in/out"),
    lower=graphs.Graph(
        name="audiocodes_established_calls_out",
        title=Title("Established calls out"),
        compound_lines=[
            "audiocodes_established_calls_out",
        ],
    ),
    upper=graphs.Graph(
        name="audiocodes_established_calls_in",
        title=Title("Established calls in"),
        compound_lines=[
            "audiocodes_established_calls_in",
        ],
    ),
)
