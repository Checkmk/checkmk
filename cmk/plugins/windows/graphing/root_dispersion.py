#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())

metric_root_dispersion = metrics.Metric(
    name="root_dispersion",
    title=Title("Root dispersion"),
    unit=UNIT_SECOND,
    color=metrics.Color.BLUE,
)
