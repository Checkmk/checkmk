#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import check_levels, get_percent_human_readable


# ==================================================================================================
# ==================================================================================================
# THIS FUNCTION HAS BEEN MIGRATED TO THE NEW CHECK API (OR IS IN THE PROCESS), PLEASE DO NOT TOUCH
# IT. INSTEAD, MODIFY THE MIGRATED VERSION.
# ==================================================================================================
# ==================================================================================================
def check_humidity(humidity, params):
    if isinstance(params, dict):
        levels = (params.get("levels") or (None, None)) + (
            params.get("levels_lower") or (None, None)
        )
    elif isinstance(params, (list, tuple)):
        # old params = (crit_low , warn_low, warn, crit)
        levels = (params[2], params[3], params[1], params[0])
    else:
        levels = None

    return check_levels(
        humidity,
        "humidity",
        levels,
        human_readable_func=get_percent_human_readable,
        boundaries=(0, 100),
    )
