#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.blade import DETECT_BLADE_BX

blade_bx_status = {
    "1": "unknown",
    "2": "disabled",
    "3": "ok",
    "4": "fail",
    "5": "prefailure-predicted",
    "6": "redundant-fan-failed",
    "7": "not-manageable",
    "8": "not-present",
    "9": "not-available",
}


def inventory_blade_bx_powerfan(info):
    for status, descr, _rpm, _max_speed, _speed, _ctrlstate in info:
        if status != "8":
            yield descr, {}


def check_blade_bx_powerfan(item, params, info):  # pylint: disable=too-many-branches
    if isinstance(params, dict):
        warn_perc_lower, crit_perc_lower = params["levels_lower"]
        warn_perc, crit_perc = params["levels"]
    else:
        warn_perc_lower, crit_perc_lower = params
        warn_perc, crit_perc = None, None

    for status, descr, rpm, max_speed, _speed, ctrlstate in info:
        if descr == item:
            speed_perc = float(rpm) * 100 / float(max_speed)
            perfdata = [
                ("perc", speed_perc, warn_perc_lower, crit_perc_lower, "0", "100"),
                ("rpm", rpm),
            ]

            if ctrlstate != "2":
                return 2, "Fan not present or poweroff", perfdata
            if status != "3":
                return 2, "Status: %s" % blade_bx_status[status], perfdata

            state = 0
            infotext = "Speed at %s RPM, %.1f%% of max" % (rpm, speed_perc)
            levels_text = ""
            if speed_perc < crit_perc_lower:
                state = 2
                levels_text = " (warn/crit below %.1f%%/%.1f%%)" % (
                    warn_perc_lower,
                    crit_perc_lower,
                )
            elif speed_perc < warn_perc_lower:
                state = 1
                levels_text = " (warn/crit below %.1f%%/%.1f%%)" % (
                    warn_perc_lower,
                    crit_perc_lower,
                )

            if warn_perc:
                if speed_perc >= crit_perc:
                    state = 2
                    levels_text = " (warn/crit at %.1f%%/%.1f%%)" % (warn_perc, crit_perc)
                elif speed_perc >= warn_perc:
                    state = 1
                    levels_text = " (warn/crit at %.1f%%/%.1f%%)" % (warn_perc, crit_perc)

            if state > 0:
                infotext += levels_text

            return state, infotext, perfdata
    return None


check_info["blade_bx_powerfan"] = LegacyCheckDefinition(
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.3.1.1",
        oids=["2", "3", "4", "5", "6", "7"],
    ),
    service_name="Blade Cooling %s",
    discovery_function=inventory_blade_bx_powerfan,
    check_function=check_blade_bx_powerfan,
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={
        "levels_lower": (20, 10),
        "levels": (80, 90),
    },
)
