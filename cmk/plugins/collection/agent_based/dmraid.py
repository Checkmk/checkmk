#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Markus Lengler <ml@lengler-it.de>

# Example outputs from agent:
#
# <<<dmraid>>>
# name   : isw_ebdabbedfh_system
# status : ok
# /dev/sda: isw, "isw_ebdabbedfh", GROUP, ok, 976773166 sectors, data@ 0 Model: WDC WD5002ABYS-5
# /dev/sdb: isw, "isw_ebdabbedfh", GROUP, ok, 976773166 sectors, data@ 0 Model: WDC WD5002ABYS-5


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_dmraid_ldisks(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=line[2]) for line in section if line[0] == "name"]


def inventory_dmraid_pdisks(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=line[0].split(":")[0]) for line in section if line[0].startswith("/dev/sd")
    ]


def check_dmraid_pdisks(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0].startswith("/dev/sd"):
            disk = line[0].split(":")[0]
            if disk == item:
                status = line[4].split(",")[0]
                if status == "ok":
                    pos = line.index("Model:")
                    model = " ".join(line[pos + 1 :])
                    yield Result(state=State.OK, summary="Online (%s)" % model)
                    return
                yield Result(state=State.CRIT, summary="Error on disk!!")
                return
    yield Result(state=State.CRIT, summary="Missing disk!!")
    return


def check_dmraid_ldisks(item: str, section: StringTable) -> CheckResult:
    LDISK_FOUND = False
    for line in section:
        if LDISK_FOUND:
            if line[0] == "status":
                status = line[2]
                if status == "ok":
                    yield Result(state=State.OK, summary="state is %s" % status)
                    return
                yield Result(state=State.CRIT, summary="%s" % status)
                return
        if line[0] == "name" and line[2] == item:
            LDISK_FOUND = True

    yield Result(state=State.UNKNOWN, summary="incomplete data from agent")
    return


def parse_dmraid(string_table: StringTable) -> StringTable:
    return string_table


agent_section_dmraid = AgentSection(name="dmraid", parse_function=parse_dmraid)

check_plugin_dmraid_ldisks = CheckPlugin(
    name="dmraid_ldisks",
    service_name="RAID LDisk %s",
    sections=["dmraid"],
    discovery_function=inventory_dmraid_ldisks,
    check_function=check_dmraid_ldisks,
)
check_plugin_dmraid_pdisks = CheckPlugin(
    name="dmraid_pdisks",
    service_name="RAID PDisk %s",
    sections=["dmraid"],
    discovery_function=inventory_dmraid_pdisks,
    check_function=check_dmraid_pdisks,
)
