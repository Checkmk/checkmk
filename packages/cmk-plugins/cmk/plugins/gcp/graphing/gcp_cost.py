#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_gcp_cost_per_month = metrics.Metric(
    name="gcp_cost_per_month",
    title=Title("Cost per month"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PINK,
)
