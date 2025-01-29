#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.acme.agent_based.lib import DETECT_ACME


def inventory_acme_realm(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=name)
        for name, _inbound, _outbound, _total_inbound, _total_outbound, _state in section
    ]


def check_acme_realm(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "3": (0, "in service"),
        "4": (1, "contraints violation"),
        "7": (2, "call load reduction"),
    }
    for name, inbound, outbound, total_inbound, total_outbound, state in section:
        if item == name:
            dev_state, dev_state_readable = map_states[state]
            yield Result(
                state=State(dev_state),
                summary=f"Status: {dev_state_readable}, Inbound: {inbound}/{total_inbound}, Outbound: {outbound}/{total_outbound}",
            )
            yield Metric("inbound", int(inbound), boundaries=(0, int(total_inbound)))
            yield Metric("outbound", int(outbound), boundaries=(0, int(total_outbound)))
            return


def parse_acme_realm(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_acme_realm = SimpleSNMPSection(
    name="acme_realm",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.2.4.1",
        oids=["2", "3", "5", "7", "11", "30"],
    ),
    parse_function=parse_acme_realm,
)
check_plugin_acme_realm = CheckPlugin(
    name="acme_realm",
    service_name="Realm %s",
    discovery_function=inventory_acme_realm,
    check_function=check_acme_realm,
)
