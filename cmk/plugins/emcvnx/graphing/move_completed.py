#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_emcvnx_move_completed = metrics.Metric(
    name="emcvnx_move_completed",
    title=Title("Data movement completed"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_emcvnx_move_completed = perfometers.Perfometer(
    name="emcvnx_move_completed",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(500000000000),
    ),
    segments=["emcvnx_move_completed"],
)
