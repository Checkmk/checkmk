#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS


def discover_enterasys_fans(section: StringTable) -> DiscoveryResult:
    for num, state in section:
        if state != "2":
            yield Service(item=num)


def check_enterasys_fans(item: str, section: StringTable) -> CheckResult:
    fan_states = {
        "1": "info not available",
        "2": "not installed",
        "3": "installed and operating",
        "4": "installed and not operating",
    }
    for num, state in section:
        if num == item:
            message = f"FAN State: {fan_states[state]}"
            if state in ["1", "2"]:
                yield Result(state=State.UNKNOWN, summary=message)
            elif state == "4":
                yield Result(state=State.CRIT, summary=message)
            else:
                yield Result(state=State.OK, summary=message)
            return


def parse_enterasys_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_enterasys_fans = SimpleSNMPSection(
    name="enterasys_fans",
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.3.1.3.1.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_enterasys_fans,
)


check_plugin_enterasys_fans = CheckPlugin(
    name="enterasys_fans",
    service_name="FAN %s",
    discovery_function=discover_enterasys_fans,
    check_function=check_enterasys_fans,
)
