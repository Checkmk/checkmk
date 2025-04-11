#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric definition for SSDs"""

from cmk.graphing.v1 import metrics, Title

metric_media_life_left = metrics.Metric(
    name="media_life_left",
    title=Title("Predicted Media Life Left"),
    unit=metrics.Unit(metrics.DecimalNotation("Percent")),
    color=metrics.Color.GREEN,
)

metric_ssd_utilization = metrics.Metric(
    name="ssd_utilization",
    title=Title("SSD Endurance Utilization"),
    unit=metrics.Unit(metrics.DecimalNotation("Percent")),
    color=metrics.Color.GREEN,
)
