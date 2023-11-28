#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metric, perfometer

perfometer_active_connections = perfometer.Perfometer(
    "active_connections",
    perfometer.FocusRange(perfometer.Closed(0), perfometer.Open(2500.0)),
    [metric.Name("active_connections")],
)
