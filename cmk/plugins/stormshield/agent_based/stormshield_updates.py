#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD

STATE_MAP = {
    "Not Available": State.WARN,
    "Broken": State.CRIT,
    "Uptodate": State.OK,
    "Disabled": State.WARN,
    "Never started": State.OK,
    "Running": State.OK,
    "Failed": State.CRIT,
}


def discover_stormshield_updates(section: StringTable) -> DiscoveryResult:
    for subsystem, state, lastrun in section:
        if state == "Failed" and lastrun == "":
            pass
        elif state not in ["Not Available", "Never started"]:
            yield Service(item=subsystem)


def check_stormshield_updates(item: str, section: StringTable) -> CheckResult:
    for subsystem, state, lastrun in section:
        if item == subsystem:
            if lastrun == "":
                lastrun = "Never"
            infotext = f"Subsystem {subsystem} is {state}, last update: {lastrun}"
            monitoringstate = STATE_MAP.get(state, State.CRIT)
            yield Result(state=monitoringstate, summary=infotext)


def parse_stormshield_updates(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_stormshield_updates = SimpleSNMPSection(
    name="stormshield_updates",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.9.1.1",
        oids=["2", "3", "4"],
    ),
    parse_function=parse_stormshield_updates,
)


check_plugin_stormshield_updates = CheckPlugin(
    name="stormshield_updates",
    service_name="Autoupdate %s",
    discovery_function=discover_stormshield_updates,
    check_function=check_stormshield_updates,
)
