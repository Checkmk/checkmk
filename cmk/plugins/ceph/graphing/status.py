#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    Unit,
)

UNIT_BYTES_PER_SECOND = Unit(IECNotation("B/s"))
UNIT_COUNTER = Unit(DecimalNotation(""), StrictPrecision(2))

metric_degraded_objects = Metric(
    name="degraded_objects",
    title=Title("Degraded Objects"),
    unit=UNIT_COUNTER,
    color=Color.DARK_PINK,
)
metric_misplaced_objects = Metric(
    name="misplaced_objects",
    title=Title("Misplaced Objects"),
    unit=UNIT_COUNTER,
    color=Color.ORANGE,
)
metric_recovering = Metric(
    name="recovering",
    title=Title("Recovering"),
    unit=UNIT_BYTES_PER_SECOND,
    color=Color.YELLOW,
)
metric_pgstates = Metric(
    name="pgstates",
    title=Title("Placement groups"),
    unit=UNIT_COUNTER,
    color=Color.DARK_BROWN,
)
