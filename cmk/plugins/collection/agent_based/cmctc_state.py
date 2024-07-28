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
from cmk.plugins.lib.cmctc import DETECT_CMCTC

# .1.3.6.1.4.1.2606.4.2.1.0 2
# .1.3.6.1.4.1.2606.4.2.2.0 1


def inventory_cmctc_state(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_cmctc_state(section: StringTable) -> CheckResult:
    status_map = {"1": "failed", "2": "ok"}

    status_code, units = section[0]
    status = status_map.get(status_code, "unknown[%s]" % status_code)

    state = State.OK if status == "ok" else State.CRIT
    infotext = f"Status: {status}, Units connected: {units}"
    yield Result(state=state, summary=infotext)


def parse_cmctc_state(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cmctc_state = SimpleSNMPSection(
    name="cmctc_state",
    detect=DETECT_CMCTC,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.4.2",
        oids=["1", "2"],
    ),
    parse_function=parse_cmctc_state,
)
check_plugin_cmctc_state = CheckPlugin(
    name="cmctc_state",
    service_name="TC unit state",
    discovery_function=inventory_cmctc_state,
    check_function=check_cmctc_state,
)
