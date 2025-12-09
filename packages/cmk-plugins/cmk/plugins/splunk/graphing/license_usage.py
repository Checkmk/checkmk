#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_splunk_slave_usage_bytes = metrics.Metric(
    name="splunk_slave_usage_bytes",
    title=Title("Slave usage bytes across all pools"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
