#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))

metric_noise_floor = metrics.Metric(
    name="noise_floor",
    title=Title("Noise floor"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.PURPLE,
)
