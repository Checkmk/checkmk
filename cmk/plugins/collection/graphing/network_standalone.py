#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.SINotation("B/s"))
UNIT_BYTES_PER_REQUEST = metrics.Unit(metrics.SINotation("B/req"))

metric_data_transfer_rate = metrics.Metric(
    name="data_transfer_rate",
    title=Title("Data transfer rate"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_request_transfer_rate = metrics.Metric(
    name="request_transfer_rate",
    title=Title("Request transfer rate"),
    unit=UNIT_BYTES_PER_REQUEST,
    color=metrics.Color.LIGHT_GREEN,
)
