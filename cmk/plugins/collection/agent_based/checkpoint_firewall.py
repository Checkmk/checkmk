#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.checkpoint import DETECT


def inventory_checkpoint_firewall(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_checkpoint_firewall(section: StringTable) -> CheckResult:
    if section:
        state, filter_name, filter_date, major, minor = section[0]
        if state.lower() == "installed":
            yield Result(
                state=State.OK,
                summary=f"{state} (v{major}.{minor}), filter: {filter_name} (since {filter_date})",
            )
            return
        yield Result(state=State.CRIT, summary="not installed, state: %s" % state)


def parse_checkpoint_firewall(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_checkpoint_firewall = SimpleSNMPSection(
    name="checkpoint_firewall",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.1",
        oids=["1", "2", "3", "8", "9"],
    ),
    parse_function=parse_checkpoint_firewall,
)
check_plugin_checkpoint_firewall = CheckPlugin(
    name="checkpoint_firewall",
    service_name="Firewall Module",
    discovery_function=inventory_checkpoint_firewall,
    check_function=check_checkpoint_firewall,
)
