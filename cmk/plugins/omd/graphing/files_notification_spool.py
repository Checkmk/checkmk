#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_new_files = metrics.Metric(
    name="new_files",
    title=Title("New files in Spool"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_deferred_files = metrics.Metric(
    name="deferred_files",
    title=Title("Deferred files in Spool"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_corrupted_files = metrics.Metric(
    name="corrupted_files",
    title=Title("Corrupted files in Spool"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)

graph_files_notification_spool = graphs.Graph(
    name="files_notification_spool",
    title=Title("Amount of files in notification spool"),
    simple_lines=[
        "new_files",
        "deferred_files",
        "corrupted_files",
    ],
    optional=[
        "deferred_files",
        "corrupted_files",
    ],
)
