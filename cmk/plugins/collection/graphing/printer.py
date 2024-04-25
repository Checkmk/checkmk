#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometers

perfometer_pages = perfometers.Perfometer(
    name="pages",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
    segments=["pages"],
)

perfometer_supply_toner_black = perfometers.Perfometer(
    name="supply_toner_black",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["supply_toner_black"],
)
