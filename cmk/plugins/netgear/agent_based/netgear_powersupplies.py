#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# .1.3.6.1.4.1.4526.10.43.1.7.1.3.1.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.1.0
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.1.1 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.1.1
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.2.0 2 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.2.0
# .1.3.6.1.4.1.4526.10.43.1.7.1.3.2.1 1 --> FASTPATH-BOXSERVICES-PRIVATE-MIB::boxServicesPowSupplyItemState.2.1


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.netgear.lib import DETECT_NETGEAR


def parse_netgear_powersupplies(string_table: StringTable) -> Mapping[str, str]:
    parsed: dict[str, str] = {}
    for oid_end, sstate in string_table:
        parsed.setdefault(oid_end.replace(".", "/"), sstate)
    return parsed


def discover_netgear_powersupplies(section: Mapping[str, str]) -> DiscoveryResult:
    yield from (Service(item=item) for item, state in section.items() if state != "1")


def check_netgear_powersupplies(item: str, section: Mapping[str, str]) -> CheckResult:
    map_states = {
        "1": (State.WARN, "not present"),
        "2": (State.OK, "operational"),
        "3": (State.CRIT, "failed"),
    }
    if (raw_state := section.get(item)) is None:
        return
    if raw_state not in map_states:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Status: unknown state {raw_state!r} (expected 1, 2 or 3)",
        )
        return
    state, state_readable = map_states[raw_state]
    yield Result(state=state, summary=f"Status: {state_readable}")


snmp_section_netgear_powersupplies = SimpleSNMPSection(
    name="netgear_powersupplies",
    detect=DETECT_NETGEAR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4526.10.43.1.7.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_netgear_powersupplies,
)


check_plugin_netgear_powersupplies = CheckPlugin(
    name="netgear_powersupplies",
    service_name="Power Supply %s",
    discovery_function=discover_netgear_powersupplies,
    check_function=check_netgear_powersupplies,
)
