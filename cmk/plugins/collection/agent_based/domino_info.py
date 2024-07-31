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
from cmk.plugins.lib.domino import DETECT

# Example SNMP walk:
#
# .1.3.6.1.4.1.334.72.2.2.0 1
# .1.3.6.1.4.1.334.72.1.1.4.8.0 MEDEMA
# .1.3.6.1.4.1.334.72.1.1.6.2.1.0 CN=HH-BK4/OU=SRV/O=MEDEMA/C=DE
# .1.3.6.1.4.1.334.72.1.1.6.2.4.0 Release 8.5.3FP5 HF89


def inventory_domino_info(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) != 0:
        yield Service()


def check_domino_info(section: StringTable) -> CheckResult:
    translate_status = {
        "1": (State.OK, "up"),
        "2": (State.CRIT, "down"),
        "3": (State.CRIT, "not-responding"),
        "4": (State.WARN, "crashed"),
        "5": (State.UNKNOWN, "unknown"),
    }
    status, domain, name, release = section[0]

    state, state_readable = translate_status[status]
    yield Result(state=state, summary="Server is %s" % state_readable)

    if len(domain) > 0:
        yield Result(state=State.OK, summary="Domain: %s" % domain)

    yield Result(state=State.OK, summary=f"Name: {name}, {release}")


def parse_domino_info(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_domino_info = SimpleSNMPSection(
    name="domino_info",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72",
        oids=["2.2", "1.1.4.8", "1.1.6.2.1", "1.1.6.2.4"],
    ),
    parse_function=parse_domino_info,
)
check_plugin_domino_info = CheckPlugin(
    name="domino_info",
    service_name="Domino Info",
    discovery_function=inventory_domino_info,
    check_function=check_domino_info,
)
