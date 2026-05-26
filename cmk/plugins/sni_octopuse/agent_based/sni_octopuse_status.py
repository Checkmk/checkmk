#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# iso.3.6.1.4.1.231.7.2.9.1.1.0 = INTEGER: 1
# The actual error state of the Octopus E PABX. Contains the highest severity level of the recent error events. This object is updated automatically, but it can also be modified manually.

# { normal(1), warning(2), minor(3), major(4), critical(5) }


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
from cmk.plugins.sni_octopuse.lib import DETECT_SNI_OCTOPUSE

_OCTOPUS_STATES_MAP = {
    1: (State.OK, "normal"),
    2: (State.WARN, "warning"),
    3: (State.WARN, "minor"),
    4: (State.CRIT, "major"),
    5: (State.CRIT, "critical"),
}


def discover_octopus_status(section: StringTable) -> DiscoveryResult:
    if len(section[0]) == 1:
        yield Service()


def check_octopus_status(section: StringTable) -> CheckResult:
    octopus_state = int(section[0][0])
    state, desc = _OCTOPUS_STATES_MAP[octopus_state]

    msg = f"PBX system state is {desc}"
    if octopus_state >= 3:
        msg += " error"
    yield Result(state=state, summary=msg)


def parse_sni_octopuse_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_sni_octopuse_status = SimpleSNMPSection(
    name="sni_octopuse_status",
    detect=DETECT_SNI_OCTOPUSE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.7.2.9.1.1",
        oids=["0"],
    ),
    parse_function=parse_sni_octopuse_status,
)


check_plugin_sni_octopuse_status = CheckPlugin(
    name="sni_octopuse_status",
    service_name="Global status",
    discovery_function=discover_octopus_status,
    check_function=check_octopus_status,
)
