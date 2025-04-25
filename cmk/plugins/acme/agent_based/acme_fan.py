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
    StringTable,
)
from cmk.plugins.acme.agent_based.lib import ACME_ENVIRONMENT_STATES, DETECT_ACME

Section = dict[str, tuple[str, str]]

# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.1 MAIN FAN1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.2 MAIN FAN2 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.3 MAIN FAN3 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.4 MAIN FAN4 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.4
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.1 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.2 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.3 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.4 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.4
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.1 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.2 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.3 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.4 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.4


def parse_acme_fan(string_table: StringTable) -> Section | None:
    section: Section = {}
    for descr, value_str, state in string_table:
        section[descr] = (value_str, state)
    return section or None


snmp_section_acme_fan = SimpleSNMPSection(
    name="acme_fan",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.3.1.4.1.1",
        oids=["3", "4", "5"],
    ),
    parse_function=parse_acme_fan,
)


def discover_acme_fan(section: Section) -> DiscoveryResult:
    yield from [
        Service(item=descr) for descr, (_value_str, state) in section.items() if state != "7"
    ]


def check_acme_fan(item: str, section: Section) -> CheckResult:
    if item in section:
        value_str, state = section[item]

        dev_state, dev_state_readable = ACME_ENVIRONMENT_STATES[state]
        yield Result(state=dev_state, summary=f"Status: {dev_state_readable}, Speed: {value_str}%")


check_plugin_acme_fan = CheckPlugin(
    name="acme_fan",
    service_name="Fan %s",
    discovery_function=discover_acme_fan,
    check_function=check_acme_fan,
)
