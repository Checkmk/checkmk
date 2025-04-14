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
from cmk.plugins.acme.agent_based.lib import DETECT_ACME


def inventory_acme_agent_sessions(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=hostname) for hostname, _agent_ty, _state in section)


def check_acme_agent_sessions(item: str, section: StringTable) -> CheckResult:
    map_states = {
        "0": (0, "disabled"),
        "1": (2, "out of service"),
        "2": (0, "standby"),
        "3": (0, "in service"),
        "4": (1, "contraints violation"),
        "5": (1, "in service timed out"),
        "6": (1, "oos provisioned response"),
    }
    for hostname, _agent_ty, state in section:
        if item == hostname:
            dev_state, dev_state_readable = map_states[state]
            yield Result(state=State(dev_state), summary="Status: %s" % dev_state_readable)
            return


def parse_acme_agent_sessions(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_acme_agent_sessions = SimpleSNMPSection(
    name="acme_agent_sessions",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.2.2.1",
        oids=["2", "3", "22"],
    ),
    parse_function=parse_acme_agent_sessions,
)
check_plugin_acme_agent_sessions = CheckPlugin(
    name="acme_agent_sessions",
    service_name="Agent sessions %s",
    discovery_function=inventory_acme_agent_sessions,
    check_function=check_acme_agent_sessions,
)
