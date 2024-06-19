#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP Walk
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.1.6 Leckagekontrolle-RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.5 Pumpe 1 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.3.2.6 Pumpe 2 RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.1.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.5 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.4.2.6 Kaeltepark RZ4
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.5.2.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.1.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.5 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.7.2.6 1
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.1.6 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.5 2
# .1.3.6.1.4.1.318.1.1.10.4.3.2.1.8.2.6 2


from collections.abc import Mapping
from dataclasses import dataclass

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
from cmk.plugins.lib.apc import DETECT


@dataclass
class Data:
    location: str
    state: tuple[str, State]


Section = Mapping[str, Data]


def parse_apc_netbotz_drycontact(string_table: StringTable) -> Section:
    parsed = {}

    state_map = {
        "1": ("Closed high mem", State.CRIT),
        "2": ("Open low mem", State.OK),
        "3": ("Disabled", State.WARN),
        "4": ("Not applicable", State.UNKNOWN),
    }

    for idx, inst, loc, state in string_table:
        parsed[inst + " " + idx] = Data(
            location=loc,
            state=state_map.get(state, (f"unknown[{state}]", State.UNKNOWN)),
        )

    return parsed


def check_apc_netbotz_drycontact(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    state_readable, state = data.state
    loc = data.location
    if loc:
        loc_info = "[%s] " % loc
    else:
        loc_info = ""
    yield Result(state=state, summary=f"{loc_info}State: {state_readable}")


def discover_apc_netbotz_drycontact(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_apc_netbotz_drycontact = SimpleSNMPSection(
    name="apc_netbotz_drycontact",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.4.3.2.1",
        oids=[OIDEnd(), "3", "4", "5"],
    ),
    parse_function=parse_apc_netbotz_drycontact,
)

check_plugin_apc_netbotz_drycontact = CheckPlugin(
    name="apc_netbotz_drycontact",
    service_name="DryContact %s",
    discovery_function=discover_apc_netbotz_drycontact,
    check_function=check_apc_netbotz_drycontact,
)
