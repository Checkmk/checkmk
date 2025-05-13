#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0))

metric_omd_broker_messages = metrics.Metric(
    name="omd_broker_messages",
    title=Title("Queued broker messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

metric_omd_application_messages = metrics.Metric(
    name="omd_application_messages",
    title=Title("Queued application messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
