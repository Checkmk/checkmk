#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, Unit

UNIT_BYTES = Unit(IECNotation("B"))

metric_mem_lnx_hardware_corrupted = Metric(
    name="mem_lnx_hardware_corrupted",
    title=Title("Hardware corrupted memory"),
    unit=UNIT_BYTES,
    color=Color.DARK_PINK,
)
