#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_mobileiron_non_compliant_summary = metrics.Metric(
    name="mobileiron_non_compliant_summary",
    title=Title("Non-compliant devices"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)

perfometer_mobileiron_non_compliant_summary = perfometers.Perfometer(
    name="mobileiron_non_compliant_summary",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["mobileiron_non_compliant_summary"],
)
