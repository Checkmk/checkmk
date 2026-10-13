#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_data_hitratio = metrics.Metric(
    name="data_hitratio",
    title=Title("Data hitratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_index_hitratio = metrics.Metric(
    name="index_hitratio",
    title=Title("Index hitratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_total_hitratio = metrics.Metric(
    name="total_hitratio",
    title=Title("Total hitratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLACK,
)
metric_xda_hitratio = metrics.Metric(
    name="xda_hitratio",
    title=Title("XDA hitratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

perfometer_total_hitratio_data_hitratio = perfometers.Bidirectional(
    name="total_hitratio_data_hitratio",
    left=perfometers.Perfometer(
        name="total_hitratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["total_hitratio"],
    ),
    right=perfometers.Perfometer(
        name="data_hitratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["data_hitratio"],
    ),
)
perfometer_index_hitratio_xda_hitratio = perfometers.Bidirectional(
    name="index_hitratio_xda_hitratio",
    left=perfometers.Perfometer(
        name="index_hitratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["index_hitratio"],
    ),
    right=perfometers.Perfometer(
        name="xda_hitratio",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["xda_hitratio"],
    ),
)

# TODO: Warum ist hier überall line? Default ist Area. Kann man die hit ratios nicht schön stacken?
# Ist nicht total die Summe der anderen?
graph_bufferpool_hitratios = graphs.Graph(
    name="bufferpool_hitratios",
    title=Title("Bufferpool Hitratios"),
    simple_lines=[
        "total_hitratio",
        "data_hitratio",
        "index_hitratio",
        "xda_hitratio",
    ],
)
