#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hitachi_hnas.lib import DETECT

check_info = {}


def discover_hitachi_hnas_fan(info):
    inventory = []
    for clusternode, fan_id, _fitted_status, _speed_status, _speed in info:
        inventory.append((clusternode + "." + fan_id, None))
    return inventory


def check_hitachi_hnas_fan(item, _no_params, info):
    fitted_status_map = (
        ("ok", 0),  # 1
        ("okIdWrong(!)", 1),  # 2
        ("notFitted(!!)", 2),  # 3
        ("unknown(!)", 1),  # 4
    )

    speed_status_map = (
        ("ok", 0),  # 1
        ("warning(!)", 1),  # 2
        ("severe(!!)", 2),  # 3
        ("unknown(!)", 1),  # 4
    )

    for clusternode, fan_id, fitted_status, speed_status, speed in info:
        if clusternode + "." + fan_id == item:
            fitted_status = int(fitted_status)
            speed_status = int(speed_status)
            speed = int(speed)
            infotext = f"PNode {clusternode} fan {fan_id}"

            worststate = 0

            # check fitted status
            name, state = fitted_status_map[fitted_status - 1]
            infotext += ", fitted status is %s" % name
            worststate = max(worststate, state)

            # check speed status
            name, state = speed_status_map[speed_status - 1]
            infotext += ", speed status is %s" % name
            worststate = max(worststate, state)

            # report speed
            infotext += ", speed is %s rpm" % speed
            perfdata = [("fanspeed", str(speed) + "rpm", "", "", 0, "")]

            return worststate, infotext, perfdata

    return 3, "No fan %s found" % item


def parse_hitachi_hnas_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["hitachi_hnas_fan"] = LegacyCheckDefinition(
    name="hitachi_hnas_fan",
    parse_function=parse_hitachi_hnas_fan,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.11.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="Fan %s",
    discovery_function=discover_hitachi_hnas_fan,
    check_function=check_hitachi_hnas_fan,
)
