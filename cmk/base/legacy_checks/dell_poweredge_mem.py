#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_mem
from cmk.plugins.dell.lib import DETECT_IDRAC_POWEREDGE

check_info = {}


def discover_dell_poweredge_mem(info):
    inventory = []
    for line in info:
        location = line[1]
        if location != "":
            inventory.append((location, None))
    return inventory


def parse_dell_poweredge_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_poweredge_mem"] = LegacyCheckDefinition(
    name="dell_poweredge_mem",
    parse_function=parse_dell_poweredge_mem,
    detect=DETECT_IDRAC_POWEREDGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5.4.1100.50.1",
        oids=["5", "8", "14", "15", "21", "22", "23"],
    ),
    service_name="%s",
    discovery_function=discover_dell_poweredge_mem,
    check_function=check_dell_poweredge_mem,
)
