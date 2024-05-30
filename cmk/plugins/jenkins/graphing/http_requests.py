#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Graphs for Jenkins system metrics: counters
"""

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

metric_jenkins_metrics_counter_http_activerequests = Metric(
    name="jenkins_metrics_counter_http_activerequests",
    title=Title("HTTP: Active Requests"),
    unit=Unit(DecimalNotation(""), StrictPrecision(0)),
    color=Color.GREEN,
)
