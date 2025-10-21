#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

metric_days_until_subscription_expiration = metrics.Metric(
    name="days_until_subscription_expiration",
    title=Title("Days until Subscription Expiration"),
    unit=metrics.Unit(metrics.DecimalNotation("days")),
    color=metrics.Color.BLUE,
)


perfometer_subscription_expiration = perfometers.Perfometer(
    name="proxmox_subscription_expiration",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(
            metrics.WarningOf("days_until_subscription_expiration"),
        ),
    ),
    segments=["days_until_subscription_expiration"],
)
