#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_ios_f_total_s_r = metrics.Metric(
    name="oracle_ios_f_total_s_r",
    title=Title("Oracle total small reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_l_r = metrics.Metric(
    name="oracle_ios_f_total_l_r",
    title=Title("Oracle total large reads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_s_w = metrics.Metric(
    name="oracle_ios_f_total_s_w",
    title=Title("Oracle total small writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_l_w = metrics.Metric(
    name="oracle_ios_f_total_l_w",
    title=Title("Oracle total large writes"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)

perfometer_oracle_ios_f_total_s_l_2 = perfometers.Bidirectional(
    name="oracle_ios_f_total_s_l_2",
    left=perfometers.Perfometer(
        name="oracle_ios_f_total_s_r",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_r",
            "oracle_ios_f_total_l_r",
        ],
    ),
    right=perfometers.Perfometer(
        name="oracle_ios_f_total_s_w",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_w",
            "oracle_ios_f_total_l_w",
        ],
    ),
)

graph_oracle_iostat_total_ios = graphs.Bidirectional(
    name="oracle_iostat_total_ios",
    title=Title("Oracle IOSTAT total IOs"),
    lower=graphs.Graph(
        name="oracle_iostat_total_ios_w",
        title=Title("Oracle IOSTAT total IO writes"),
        simple_lines=[
            "oracle_ios_f_total_s_w",
            "oracle_ios_f_total_l_w",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_total_ios_r",
        title=Title("Oracle IOSTAT total IO reads"),
        simple_lines=[
            "oracle_ios_f_total_s_r",
            "oracle_ios_f_total_l_r",
        ],
    ),
)
