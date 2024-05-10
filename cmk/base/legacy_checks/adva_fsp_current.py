#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.1.101318912  8110
# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.2.101318912  65600
# .1.3.6.1.4.1.2544.1.11.2.4.2.2.1.3.101318912  9
# .1.3.6.1.4.1.2544.2.5.5.1.1.1.101318912  "PSU/7HU-AC-800"
# .1.3.6.1.4.1.2544.2.5.5.1.1.5.101318912  "MOD-1-1"


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import equals, SNMPTree, StringTable


def inventory_adva_fsp_current(info):
    for _current_str, _upper_threshold_str, power_str, _unit_name, index_aid in info:
        # Ignore non-connected sensors
        if index_aid != "" and power_str != "":
            yield index_aid, None


def check_adva_fsp_current(item, _no_params, info):
    for current_str, upper_threshold_str, _power_str, unit_name, index_aid in info:
        if index_aid == item:
            current = float(current_str) / 1000.0
            upper_threshold = float(upper_threshold_str) / 1000

            infotext = f"[{unit_name}] {current:.3f} A (crit at {upper_threshold:.3f} A)"
            perfdata = [
                (
                    "current",
                    current,
                    None,
                    upper_threshold,
                )
            ]

            if current <= 0:
                return 3, "Invalid sensor data"
            if current >= upper_threshold:
                return 2, infotext, perfdata
            return 0, infotext, perfdata
    return None


def parse_adva_fsp_current(string_table: StringTable) -> StringTable:
    return string_table


check_info["adva_fsp_current"] = LegacyCheckDefinition(
    parse_function=parse_adva_fsp_current,
    detect=equals(".1.3.6.1.2.1.1.1.0", "Fiber Service Platform F7"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2544",
        oids=[
            "1.11.2.4.2.2.1.1",
            "1.11.2.4.2.2.1.2",
            "1.11.2.4.2.2.1.3",
            "2.5.5.1.1.1",
            "2.5.5.2.1.5",
        ],
    ),
    service_name="Power Supply %s",
    discovery_function=inventory_adva_fsp_current,
    check_function=check_adva_fsp_current,
)
