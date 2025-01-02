#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

metric_mail_transfer_threads = metrics.Metric(
    name="cisco_sma_mail_transfer_threads",
    title=Title("Mail transfer threads"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.ORANGE,
)
