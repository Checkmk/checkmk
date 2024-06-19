#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_graylog_input = metrics.Metric(
    name="graylog_input",
    title=Title("Input traffic"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_graylog_output = metrics.Metric(
    name="graylog_output",
    title=Title("Output traffic"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_graylog_decoded = metrics.Metric(
    name="graylog_decoded",
    title=Title("Decoded traffic"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BLUE,
)
