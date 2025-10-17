#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# healthy
# <<<pvecm_status:sep(58)>>>
# Version: 6.2.0
# Config Version: 35
# status Id: 27764
# status Member: Yes
# status Generation: 36032
# Membership state: status-Member
# Nodes: 7
# Expected votes: 7
# Total votes: 7
# Node votes: 1
# Quorum: 4
# Active subsystems: 1
# Flags:
# Ports Bound: 0
# Node name: host-FOO
# Node ID: 5
# Multicast addresses: aaa.bbb.ccc.ddd
# Node addresses: nnn.mmm.ooo.ppp

# with problems:
# <<<pvecm_status:sep(58)>>>
# cman_tool: Cannot open connection to cman, is it running?

# <<<pvecm_status:sep(58)>>>
# Version: 6.2.0
# Config Version: 2
# status Id: 4921
# status Member: Yes
# status Generation: 280
# Membership state: status-Member
# Nodes: 1
# Expected votes: 2
# Total votes: 1
# Node votes: 1
# Quorum: 2 Activity blocked
# Active subsystems: 5
# Flags:
# Ports Bound: 0
# Node name: host-FOO
# Node ID: 1
# Multicast addresses: aaa.bbb.ccc.ddd
# Node addresses: nnn.mmm.ooo.ppp


from collections.abc import Mapping

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

type Section = Mapping[str, str]


def parse_pvecm_status(string_table: StringTable) -> Section:
    parsed = dict[str, str]()
    for line in string_table:
        if len(line) < 2:
            continue
        k = line[0].strip().lower()
        if k == "date":
            v = ":".join(line[1:]).strip()
        else:
            v = " ".join(line[1:]).strip()
        parsed.setdefault(k, v)
    return parsed


def inventory_pvecm_status(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_pvecm_status(section: Section) -> CheckResult:
    if "cman_tool" in section and "cannot open connection to cman" in section["cman_tool"]:
        yield Result(state=State.CRIT, summary="Cluster management tool: %s" % section["cman_tool"])

    else:
        name = section.get("cluster name", section.get("quorum provider", "unknown"))

        yield Result(state=State.OK, summary="Name: {}, Nodes: {}".format(name, section["nodes"]))

        if "activity blocked" in section["quorum"]:
            yield Result(state=State.CRIT, summary="Quorum: %s" % section["quorum"])

        if int(section["expected votes"]) == int(section["total votes"]):
            yield Result(state=State.OK, summary="No faults")
        else:
            yield Result(
                state=State.CRIT,
                summary="Expected votes: {}, Total votes: {}".format(
                    section["expected votes"],
                    section["total votes"],
                ),
            )


agent_section_pvecm_status = AgentSection(
    name="pvecm_status",
    parse_function=parse_pvecm_status,
)


check_plugin_pvecm_status = CheckPlugin(
    name="pvecm_status",
    service_name="PVE Cluster State",
    discovery_function=inventory_pvecm_status,
    check_function=check_pvecm_status,
)
