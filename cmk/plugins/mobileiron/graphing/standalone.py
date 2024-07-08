#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_mobileiron_last_build = metrics.Metric(
    name="mobileiron_last_build",
    title=Title("Age of OS build version"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
