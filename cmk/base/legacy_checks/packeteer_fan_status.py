#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, startswith, StringTable

check_info = {}


def discover_packeteer_fan_status(section: StringTable) -> DiscoveryResult:
    for nr, fan_status in enumerate(section[0]):
        if fan_status in ["1", "2"]:
            yield Service(item=f"{nr}")


def check_packeteer_fan_status(item, _no_params, info):
    fan_status = info[0][int(item)]
    if fan_status == "1":
        return 0, "OK"
    if fan_status == "2":
        return 2, "Not OK"
    if fan_status == "3":
        return 2, "Not present"
    return None


def parse_packeteer_fan_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["packeteer_fan_status"] = LegacyCheckDefinition(
    name="packeteer_fan_status",
    parse_function=parse_packeteer_fan_status,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2334"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2334.2.1.5",
        oids=["12", "14", "22", "24"],
    ),
    service_name="Fan Status",
    discovery_function=discover_packeteer_fan_status,
    check_function=check_packeteer_fan_status,
)
