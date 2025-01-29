#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    DiscoveryResult,
    exists,
    Service,
    SNMPTree,
    startswith,
    StringTable,
)

check_info = {}


def discover_fsc_subsystems(string_table: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in string_table if int(line[1]) > 0)


def check_fsc_subsystems(item, _no_params, info):
    for line in info:  # , value1, value2 in info:
        name = line[0]
        if name != item:
            continue
        if line[1] == "":
            return 3, "Status not found in SNMP data"
        status = int(line[1])
        statusname = {1: "ok", 2: "degraded", 3: "error", 4: "failed", 5: "unknown-init"}.get(
            status, "invalid"
        )
        if status in {1, 5}:
            return (0, "%s - no problems" % statusname)
        if 2 <= status <= 4:
            return (2, "%s" % statusname)
        return (3, "unknown status %d" % status)


def parse_fsc_subsystems(string_table: StringTable) -> StringTable:
    return string_table


check_info["fsc_subsystems"] = LegacyCheckDefinition(
    name="fsc_subsystems",
    parse_function=parse_fsc_subsystems,
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
        ),
        exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.11.3.1.1",
        oids=["2", "3"],
    ),
    service_name="FSC %s",
    discovery_function=discover_fsc_subsystems,
    check_function=check_fsc_subsystems,
)
