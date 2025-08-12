#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))


metric_audiocodes_abnormal_terminated_calls_in_total = metrics.Metric(
    name="audiocodes_abnormal_terminated_calls_in_total",
    title=Title("Abnormal terminated calls in"),
    unit=UNIT_COUNT,
    color=metrics.Color.DARK_ORANGE,
)

metric_audiocodes_abnormal_terminated_calls_out_total = metrics.Metric(
    name="audiocodes_abnormal_terminated_calls_out_total",
    title=Title("Abnormal terminated calls out"),
    unit=UNIT_COUNT,
    color=metrics.Color.LIGHT_BROWN,
)

graph_audiocodes_abnormal_terminated_calls_in_out = graphs.Bidirectional(
    name="audiocodes_abnormal_terminated_calls_in_out",
    title=Title("Abnormal terminated calls in/out"),
    lower=graphs.Graph(
        name="audiocodes_abnormal_terminated_calls_out_total",
        title=Title("Abnormal terminated calls out"),
        compound_lines=[
            "audiocodes_abnormal_terminated_calls_out_total",
        ],
    ),
    upper=graphs.Graph(
        name="audiocodes_abnormal_terminated_calls_in_total",
        title=Title("Abnormal terminated calls in"),
        compound_lines=[
            "audiocodes_abnormal_terminated_calls_in_total",
        ],
    ),
)
