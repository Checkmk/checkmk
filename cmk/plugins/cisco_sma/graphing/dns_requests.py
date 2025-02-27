#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))

metric_outstanding_dns_requests = metrics.Metric(
    name="outstanding_dns_requests",
    title=Title("Outstanding DNS requests"),
    unit=UNIT_COUNT,
    color=metrics.Color.BLUE,
)

metric_pending_dns_requests = metrics.Metric(
    name="pending_dns_requests",
    title=Title("Pending DNS requests"),
    unit=UNIT_COUNT,
    color=metrics.Color.ORANGE,
)
