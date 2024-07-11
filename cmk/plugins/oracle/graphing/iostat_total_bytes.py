#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_oracle_ios_f_total_s_rb = metrics.Metric(
    name="oracle_ios_f_total_s_rb",
    title=Title("Oracle total small read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_l_rb = metrics.Metric(
    name="oracle_ios_f_total_l_rb",
    title=Title("Oracle total large read bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_oracle_ios_f_total_s_wb = metrics.Metric(
    name="oracle_ios_f_total_s_wb",
    title=Title("Oracle total small write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_ios_f_total_l_wb = metrics.Metric(
    name="oracle_ios_f_total_l_wb",
    title=Title("Oracle total large write bytes"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)

perfometer_oracle_ios_f_total_s_l_1 = perfometers.Bidirectional(
    name="oracle_ios_f_total_s_l_1",
    left=perfometers.Perfometer(
        name="oracle_ios_f_total_rb",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_rb",
            "oracle_ios_f_total_l_rb",
        ],
    ),
    right=perfometers.Perfometer(
        name="oracle_ios_f_total_wb",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=[
            "oracle_ios_f_total_s_wb",
            "oracle_ios_f_total_l_wb",
        ],
    ),
)

graph_oracle_iostat_total_bytes = graphs.Bidirectional(
    name="oracle_iostat_total_bytes",
    title=Title("Oracle IOSTAT total bytes"),
    lower=graphs.Graph(
        name="oracle_iostat_total_wbytes",
        title=Title("Oracle IOSTAT total writes bytes"),
        simple_lines=[
            "oracle_ios_f_total_s_wb",
            "oracle_ios_f_total_l_wb",
        ],
    ),
    upper=graphs.Graph(
        name="oracle_iostat_total_rbytes",
        title=Title("Oracle IOSTAT total read bytes"),
        simple_lines=[
            "oracle_ios_f_total_s_rb",
            "oracle_ios_f_total_l_rb",
        ],
    ),
)
