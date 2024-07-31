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
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_esmlog(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_dell_om_esmlog(section: StringTable) -> CheckResult:
    status = int(section[0][0])
    if status == 5:
        yield Result(state=State.CRIT, summary="ESM Log is full")
    elif status == 3:
        yield Result(state=State.OK, summary="ESM Log is less than 80% full")
    else:
        yield Result(state=State.WARN, summary="ESM Log is more than 80% full")


def parse_dell_om_esmlog(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_dell_om_esmlog = SimpleSNMPSection(
    name="dell_om_esmlog",
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.200.10.1.41",
        oids=["1"],
    ),
    parse_function=parse_dell_om_esmlog,
)
check_plugin_dell_om_esmlog = CheckPlugin(
    name="dell_om_esmlog",
    service_name="ESM Log",
    discovery_function=inventory_dell_om_esmlog,
    check_function=check_dell_om_esmlog,
)
