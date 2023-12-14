#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometer

perfometer_active_connections = perfometer.Perfometer(
    name="active_connections",
    focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Open(565)),
    segments=["active_connections"],
)
