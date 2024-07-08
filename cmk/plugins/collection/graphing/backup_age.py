#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_backup_age = metrics.Metric(
    name="backup_age",
    title=Title("Time since last backup"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_checkpoint_age = metrics.Metric(
    name="checkpoint_age",
    title=Title("Time since last checkpoint"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

perfometer_backup_age_checkpoint_age = perfometers.Stacked(
    name="backup_age_checkpoint_age",
    lower=perfometers.Perfometer(
        name="backup_age",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(200000),
        ),
        segments=["backup_age"],
    ),
    upper=perfometers.Perfometer(
        name="checkpoint_age",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(200000),
        ),
        segments=["checkpoint_age"],
    ),
)
perfometer_backup_age = perfometers.Perfometer(
    name="backup_age",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200000),
    ),
    segments=["backup_age"],
)

graph_backup_time = graphs.Graph(
    name="backup_time",
    title=Title("Backup time"),
    compound_lines=[
        "checkpoint_age",
        "backup_age",
    ],
)
