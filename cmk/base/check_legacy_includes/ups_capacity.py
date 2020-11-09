#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import get_age_human_readable
from cmk.base.check_api import get_percent_human_readable
from cmk.base.check_api import check_levels


def check_ups_capacity(_item, params, info):
    # To support inventories with the old version
    if isinstance(params, tuple):  # old format with 2 params in tuple
        warn, crit = params
        cap_warn, cap_crit = (95, 90)
    elif isinstance(params, dict):  # new dict format
        warn, crit = params.get('battime', (0, 0))
        cap_warn, cap_crit = params.get('capacity', (95, 90))
    else:
        warn, crit = (0, 0)
        cap_warn, cap_crit = (95, 90)

    minutes_on_bat, minutes_left, percent_fuel = (
        int(num) if num.strip() else None  #
        for num in info[0])
    on_battery = minutes_left is not None and minutes_on_bat

    # Check time left on battery
    # `minutes_left` can be 0 which not always means that there's no time left but the device might
    # also just be on main power supply
    if on_battery:
        yield check_levels(
            minutes_left * 60,
            "capacity",
            (None, None, warn * 60, crit * 60),
            human_readable_func=get_age_human_readable,
            infoname="Minutes left",
        )
    else:
        yield 0, "on mains"

    # Check percentual capacity - note that capacity will only be checked on battery
    if percent_fuel is not None:
        yield check_levels(
            percent_fuel,
            "percent",
            (None, None, cap_warn, cap_crit) if on_battery else None,
            human_readable_func=get_percent_human_readable,
            infoname="Percent",
        )

    # Output time on battery
    if minutes_on_bat is not None and minutes_on_bat > 0:
        yield 0, "Time running on battery: %s" % get_age_human_readable(minutes_on_bat * 60)
