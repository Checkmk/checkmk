#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.hp_proliant.lib import DETECT, STATUS_MAP

check_info = {}

hp_proliant_status2nagios_map = {k: int(v) for k, v in STATUS_MAP.items()}


hp_proliant_locale = {
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
    14: "managementBoard",
    15: "backplane",
    16: "networkSlot",
    17: "bladeSlot",
    18: "virtual",
}

hp_proliant_status_map = {
    1: "unknown",
    2: "ok",
    3: "degraded",
    4: "failed",
    5: "disabled",
}


def parse_hp_proliant_temp(string_table: StringTable) -> StringTable:
    return string_table


def format_hp_proliant_name(line):
    return f"{line[0]} ({hp_proliant_locale[int(line[1])]})"


def discover_hp_proliant_temp(info):
    for line in info:
        if line[-1] != "1":
            # other(1): Temperature could not be determined
            yield format_hp_proliant_name(line), {}


def check_hp_proliant_temp(item, params, info):
    for line in info:
        if format_hp_proliant_name(line) == item:
            value, threshold, status = line[2:]

            # This case means no threshold available and
            # the devices' web interface displays "N/A"
            if threshold in ("-99", "0"):
                devlevels = None
            else:
                threshold = float(threshold)
                devlevels = (threshold, threshold)

            snmp_status = hp_proliant_status_map[int(status)]

            return check_temperature(
                float(value),
                params,
                "hp_proliant_temp_%s" % item,
                dev_levels=devlevels,
                dev_status=hp_proliant_status2nagios_map[snmp_status],
                dev_status_name="Unit: %s" % snmp_status,
            )
    return 3, "item not found in snmp data"


check_info["hp_proliant_temp"] = LegacyCheckDefinition(
    name="hp_proliant_temp",
    parse_function=parse_hp_proliant_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.6.8.1",
        oids=["2", "3", "4", "5", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_hp_proliant_temp,
    check_function=check_hp_proliant_temp,
    check_ruleset_name="temperature",
)
