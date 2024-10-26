#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from datetime import timedelta

from cmk.agent_based.legacy.v0_unstable import check_levels

# Example for params:
# {
#    "min" : ( 7200, 3600 ),            # Minimum required uptime (warn, crit)
#    "max" : ( 86400 * 7, 86400 * 14),  # Maximum required uptime (warn, crit)
# }


################################################################################################
#  NOTE: This function has already been migrated to cmk.plugins.collection.agent_based.snmp_uptime   #
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
