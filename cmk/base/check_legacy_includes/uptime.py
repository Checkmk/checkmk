#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
import time

from cmk.base.check_api import check_levels


################################################################################################
#  NOTE: This function has already been migrated to cmk.base.plugins.agent_based.snmp_uptime   #
#         Plugins that use this function should probably just subscribe to the snmp_uptime     #
#         section!                                                                             #
################################################################################################
def parse_snmp_uptime(ticks):
    if len(ticks) < 3:
        return 0

    try:
        return int(ticks[:-2])
    except Exception:
        pass

    try:
        days, h, m, s = ticks.split(":")
        return (int(days) * 86400) + (int(h) * 3600) + (int(m) * 60) + int(float(s))
    except Exception:
        pass

    return 0


# Example for params:
# {
#    "min" : ( 7200, 3600 ),            # Minimum required uptime (warn, crit)
#    "max" : ( 86400 * 7, 86400 * 14),  # Maximum required uptime (warn, crit)
# }

from datetime import timedelta


################################################################################################
#  NOTE: This function has already been migrated to cmk.base.plugins.agent_based.snmp_uptime   #
################################################################################################
def check_uptime_seconds(params, uptime_sec):

    if params is None:  # legacy: support older versions of parameters
        params = {}

    params = params.get("max", (None, None)) + params.get("min", (None, None))
    return check_levels(
        uptime_sec,
        "uptime",
        params,
        human_readable_func=lambda x: timedelta(seconds=int(x)),
        infoname="Up since %s, uptime"
        % time.strftime("%c", time.localtime(time.time() - uptime_sec)),
    )
