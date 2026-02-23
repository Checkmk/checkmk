#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import metrics, Title

metric_channel_width = metrics.Metric(
    name="channel_width",
    title=Title("Channel width"),
    unit=metrics.Unit(metrics.SINotation("hZ")),
    color=metrics.Color.BLUE,
)

metric_channel = metrics.Metric(
    name="channel",
    title=Title("Radio channel"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.DARK_YELLOW,
)
