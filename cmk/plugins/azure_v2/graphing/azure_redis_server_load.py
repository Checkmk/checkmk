#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_azure_redis_server_load = metrics.Metric(
    name="azure_redis_server_load",
    title=Title("Server load"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)

# We show the instantaneous number here even if averaging is enabled. Probably
# non-ideal but otherwise we'd have to emit a third metric that always gets
# updated whether or not averaging was enabled, and then we'd get extra graphs.
perfometer_azure_redis_server_load = perfometers.Perfometer(
    name="azure_redis_server_load",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["azure_redis_server_load"],
)
