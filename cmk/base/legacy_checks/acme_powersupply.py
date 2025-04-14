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
from cmk.plugins.acme.agent_based.lib import ACME_ENVIRONMENT_STATES, DETECT_ACME

Section = dict[str, str]

# .1.3.6.1.4.1.9148.3.3.1.5.1.1.3.1 Power Supply A --> ACMEPACKET-ENVMON-MIB::apEnvMonPowerSupplyStatusDescr.1
# .1.3.6.1.4.1.9148.3.3.1.5.1.1.3.2 Power Supply B --> ACMEPACKET-ENVMON-MIB::apEnvMonPowerSupplyStatusDescr.2
# .1.3.6.1.4.1.9148.3.3.1.5.1.1.4.1 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonPowerSupplyState.1
# .1.3.6.1.4.1.9148.3.3.1.5.1.1.4.2 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonPowerSupplyState.2


def inventory_acme_powersupply(section: Section) -> DiscoveryResult:
    if section:
        yield from [Service(item=descr) for descr, state in section.items() if state != "7"]


def check_acme_powersupply(item: str, section: Section) -> CheckResult:
    state = section[item]
    dev_state, dev_state_readable = ACME_ENVIRONMENT_STATES[state]
    yield Result(state=State(dev_state), summary="Status: %s" % dev_state_readable)


def parse_acme_powersupply(string_table: StringTable) -> Section | None:
    section: Section = {}
    for descr, state in string_table:
        section[descr] = state
    return section or None


snmp_section_acme_powersupply = SimpleSNMPSection(
    name="acme_powersupply",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.3.1.5.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_acme_powersupply,
)
check_plugin_acme_powersupply = CheckPlugin(
    name="acme_powersupply",
    service_name="Power supply %s",
    discovery_function=inventory_acme_powersupply,
    check_function=check_acme_powersupply,
)
