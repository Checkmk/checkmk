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
from cmk.plugins.ups.lib_socomec import DETECT_SOCOMEC

# This is from the old (v5.01) MIB and is incompatible with the new one below
#    ups_socomec_source_states = {
#        1: (3, "Other"),
#        2: (2, "Offline"),
#        3: (0, "Normal"),
#        4: (1, "Internal Maintenance Bypass"),
#        5: (2, "On battery"),
#        6: (0, "Booster"),
#        7: (0, "Reducer"),
#        8: (0, "Standby"),
#        9: (0, "Eco mode"),
#    }

# This is from the new (v6) MIB
_SOURCE_STATES: dict[int, tuple[State, str]] = {
    1: (State.UNKNOWN, "Unknown"),
    2: (State.CRIT, "On inverter"),
    3: (State.OK, "On mains"),
    4: (State.OK, "Eco mode"),
    5: (State.WARN, "On bypass"),
    6: (State.OK, "Standby"),
    7: (State.WARN, "On maintenance bypass"),
    8: (State.CRIT, "UPS off"),
    9: (State.OK, "Normal mode"),
}


def parse_ups_socomec_out_source(string_table: StringTable) -> StringTable:
    return string_table


def discover_ups_socomec_out_source(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_ups_socomec_out_source(section: StringTable) -> CheckResult:
    state, text = _SOURCE_STATES[int(section[0][0])]
    yield Result(state=state, summary=text)


snmp_section_ups_socomec_out_source = SimpleSNMPSection(
    name="ups_socomec_out_source",
    detect=DETECT_SOCOMEC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4555.1.1.1.1.4",
        oids=["1"],
    ),
    parse_function=parse_ups_socomec_out_source,
)


check_plugin_ups_socomec_out_source = CheckPlugin(
    name="ups_socomec_out_source",
    service_name="Output Source",
    discovery_function=discover_ups_socomec_out_source,
    check_function=check_ups_socomec_out_source,
)
