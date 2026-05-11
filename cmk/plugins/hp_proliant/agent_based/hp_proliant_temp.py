#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.hp_proliant.lib import DETECT, STATUS_MAP
from cmk.plugins.lib.temperature import check_temperature, TempParamType

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


Section = Sequence[Sequence[str]]


def parse_hp_proliant_temp(string_table: StringTable) -> Section:
    return string_table


def _format_hp_proliant_name(line: Sequence[str]) -> str:
    return f"{line[0]} ({hp_proliant_locale[int(line[1])]})"


def discover_hp_proliant_temp(section: Section) -> DiscoveryResult:
    for line in section:
        if line[-1] != "1":
            # other(1): Temperature could not be determined
            yield Service(item=_format_hp_proliant_name(line))


def check_hp_proliant_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    for line in section:
        if _format_hp_proliant_name(line) != item:
            continue
        value, threshold, status = line[2:]

        # This case means no threshold available and
        # the devices' web interface displays "N/A"
        if threshold in ("-99", "0"):
            dev_levels = None
        else:
            threshold_f = float(threshold)
            dev_levels = (threshold_f, threshold_f)

        snmp_status = hp_proliant_status_map[int(status)]

        yield from check_temperature(
            float(value),
            params,
            dev_levels=dev_levels,
            dev_status=int(STATUS_MAP[snmp_status]),
            dev_status_name=f"Unit: {snmp_status}",
        )
        return


snmp_section_hp_proliant_temp = SimpleSNMPSection(
    name="hp_proliant_temp",
    parse_function=parse_hp_proliant_temp,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.6.8.1",
        oids=["2", "3", "4", "5", "6"],
    ),
)


check_plugin_hp_proliant_temp = CheckPlugin(
    name="hp_proliant_temp",
    service_name="Temperature %s",
    discovery_function=discover_hp_proliant_temp,
    check_function=check_hp_proliant_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
