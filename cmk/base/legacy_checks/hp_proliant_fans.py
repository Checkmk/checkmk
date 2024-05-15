#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.hp_proliant import hp_proliant_status2nagios_map, sanitize_item
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.hp_proliant import DETECT

hp_proliant_fans_status_map = {1: "other", 2: "ok", 3: "degraded", 4: "failed"}
hp_proliant_speed_map = {1: "other", 2: "normal", 3: "high"}
hp_proliant_fans_locale = {
    1: "other",
    2: "unknown",
    3: "system",
    4: "systemBoard",
    5: "ioBoard",
    6: "cpu",
    7: "memory",
    8: "storage",
    9: "removableMedia",
    10: "powerSupply",
    11: "ambient",
    12: "chassis",
    13: "bridgeCard",
}


def parse_hp_proliant_fans(string_table: StringTable) -> StringTable:
    return string_table


def inventory_hp_proliant_fans(info):
    for line in [l for l in info if l[2] == "3"]:
        label = hp_proliant_fans_locale.get(int(line[1]), "other")
        yield sanitize_item(f"{line[0]} ({label})"), {}


def check_hp_proliant_fans(item, params, info):
    for line in info:
        label = "other"
        if len(line) > 1 and int(line[1]) in hp_proliant_fans_locale:
            label = hp_proliant_fans_locale[int(line[1])]

        if sanitize_item(f"{line[0]} ({label})") == item:
            index, _name, _present, speed, status, currentSpeed = line
            snmp_status = hp_proliant_fans_status_map[int(status)]
            status = hp_proliant_status2nagios_map[snmp_status]

            detailOutput = ""
            perfdata = []
            if currentSpeed != "":
                detailOutput = ", RPM: %s" % currentSpeed
                perfdata = [("temp", int(currentSpeed))]

            return (
                status,
                f'FAN Sensor {index} "{label}", Speed is {hp_proliant_speed_map[int(speed)]}, State is {snmp_status}{detailOutput}',
                perfdata,
            )
    return (3, "item not found in snmp data")


check_info["hp_proliant_fans"] = LegacyCheckDefinition(
    parse_function=parse_hp_proliant_fans,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.6.7.1",
        oids=["2", "3", "4", "6", "9", "12"],
    ),
    service_name="HW FAN%s",
    discovery_function=inventory_hp_proliant_fans,
    check_function=check_hp_proliant_fans,
)
