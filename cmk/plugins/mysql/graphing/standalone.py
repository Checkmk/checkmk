#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_relay_log_space = metrics.Metric(
    name="relay_log_space",
    title=Title("Relay log size"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BROWN,
)
