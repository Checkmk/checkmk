#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

epson_beamer_lamp_default_levels = (1000 * 3600, 1500 * 3600)


def inventory_epson_beamer_lamp(info):
    if info:
        return [(None, epson_beamer_lamp_default_levels)]
    return []


def check_epson_beamer_lamp(_no_item, params, info):
    lamp_hrs = int(info[0][0])
    lamp_time = lamp_hrs * 3600
    status = 0
    infotext = "Operation time: %d h" % lamp_hrs
    if params:
        warn, crit = params
        levelstext = " (warn/crit at %.0f/%.0f hours)" % tuple(x / 3600.0 for x in params)
        if lamp_time >= crit:
            status = 2
        elif lamp_time >= warn:
            status = 1
        if status:
            infotext += levelstext
    return status, infotext


check_info["epson_beamer_lamp"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", "1248"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1248.4.1.1.1.1",
        oids=["0"],
    ),
    service_name="Beamer Lamp",
    discovery_function=inventory_epson_beamer_lamp,
    check_function=check_epson_beamer_lamp,
    check_ruleset_name="lamp_operation_time",
)
