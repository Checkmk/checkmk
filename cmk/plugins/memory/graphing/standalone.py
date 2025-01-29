#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_percpu = Metric(
    name="percpu",
    title=Title("Memory allocated to percpu"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_kreclaimable = Metric(
    name="kreclaimable",
    title=Title("Reclaimable kernel allocations"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_sreclaimable = Metric(
    name="sreclaimable",
    title=Title("Reclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_sunreclaim = Metric(
    name="sunreclaim",
    title=Title("Unreclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
