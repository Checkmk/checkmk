#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12148.9.2.2.0 1 --> ELTEK-DISTRIBUTED-MIB::systemOperationalStatus.0


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
from cmk.plugins.eltek.lib import DETECT_ELTEK


def inventory_eltek_systemstatus(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_eltek_systemstatus(section: StringTable) -> CheckResult:
    map_state = {
        "0": (State.CRIT, "float, voltage regulated"),
        "1": (State.OK, "float, temperature comp. regulated"),
        "2": (State.CRIT, "battery boost"),
        "3": (State.CRIT, "battery test"),
    }
    state, state_readable = map_state[section[0][0]]
    yield Result(state=state, summary="Operational status: %s" % state_readable)
    return


def parse_eltek_systemstatus(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_eltek_systemstatus = SimpleSNMPSection(
    name="eltek_systemstatus",
    detect=DETECT_ELTEK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12148.9.2",
        oids=["2"],
    ),
    parse_function=parse_eltek_systemstatus,
)


check_plugin_eltek_systemstatus = CheckPlugin(
    name="eltek_systemstatus",
    service_name="System Status",
    discovery_function=inventory_eltek_systemstatus,
    check_function=check_eltek_systemstatus,
)
