#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.3652.3.2.3.1.2.1 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.1
# .1.3.6.1.4.1.3652.3.2.3.1.2.2 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.2
# .1.3.6.1.4.1.3652.3.2.3.1.2.3 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.3
# .1.3.6.1.4.1.3652.3.2.3.1.2.4 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.4
# .1.3.6.1.4.1.3652.3.2.3.1.2.5 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.5
# .1.3.6.1.4.1.3652.3.2.3.1.2.6 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.6
# .1.3.6.1.4.1.3652.3.2.3.1.2.7 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.7
# .1.3.6.1.4.1.3652.3.2.3.1.2.8 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.8
# .1.3.6.1.4.1.3652.3.2.3.1.2.9 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.9
# .1.3.6.1.4.1.3652.3.2.3.1.2.10 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.10


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
from cmk.plugins.pandacom.lib import DETECT_PANDACOM


def inventory_pandacom_fan(section: StringTable) -> DiscoveryResult:
    for fan_nr, fan_state in section:
        if fan_state not in ["0", "5"]:
            yield Service(item=fan_nr)


def check_pandacom_fan(item: str, section: StringTable) -> CheckResult:
    map_fan_state = {
        "0": (State.UNKNOWN, "not available"),
        "1": (State.OK, "on"),
        "2": (State.CRIT, "off"),
        "3": (State.OK, "pass"),
        "4": (State.CRIT, "fail"),
        "5": (State.UNKNOWN, "not installed"),
        "6": (State.OK, "auto"),
    }
    for fan_nr, fan_state in section:
        if fan_nr == item:
            state, state_readable = map_fan_state[fan_state]
            yield Result(state=state, summary=f"Operational status: {state_readable}")
            return


def parse_pandacom_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_pandacom_fan = SimpleSNMPSection(
    name="pandacom_fan",
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.2.3.1",
        oids=["1", "2"],
    ),
    parse_function=parse_pandacom_fan,
)


check_plugin_pandacom_fan = CheckPlugin(
    name="pandacom_fan",
    service_name="Fan %s",
    discovery_function=inventory_pandacom_fan,
    check_function=check_pandacom_fan,
)
