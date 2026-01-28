#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_amperage
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

check_info = {}


def discover_dell_poweredge_amperage_power(info: StringTable) -> list[tuple[str, None]]:
    inventory = []
    for line in info:
        if line[6] != "" and line[5] in ("24", "26"):
            inventory.append((line[6], None))
    return inventory


def discover_dell_poweredge_amperage_current(info: StringTable) -> list[tuple[str, None]]:
    inventory = []
    for line in info:
        if line[6] != "" and line[5] in ("23", "25"):
            inventory.append((line[6], None))
    return inventory


def parse_dell_poweredge_amperage(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_poweredge_amperage"] = LegacyCheckDefinition(
    name="dell_poweredge_amperage",
    parse_function=parse_dell_poweredge_amperage,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.600.30.1",
        oids=["1", "2", "4", "5", "6", "7", "8", "10", "11"],
    ),
)

check_info["dell_poweredge_amperage.power"] = LegacyCheckDefinition(
    name="dell_poweredge_amperage_power",
    service_name="%s",
    sections=["dell_poweredge_amperage"],
    discovery_function=discover_dell_poweredge_amperage_power,
    check_function=check_dell_poweredge_amperage,
)

check_info["dell_poweredge_amperage.current"] = LegacyCheckDefinition(
    name="dell_poweredge_amperage_current",
    service_name="%s",
    sections=["dell_poweredge_amperage"],
    discovery_function=discover_dell_poweredge_amperage_current,
    check_function=check_dell_poweredge_amperage,
)
