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

from .detection import DETECT_BLADE_BX


def inventory_blade_bx_powermod(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_blade_bx_powermod(item: str, section: StringTable) -> CheckResult:
    power_status = {
        "1": ("unknown", State.UNKNOWN),
        "2": ("ok", State.OK),
        "3": ("not-present", State.CRIT),
        "4": ("error", State.CRIT),
        "5": ("critical", State.CRIT),
        "6": ("off", State.CRIT),
        "7": ("dummy", State.CRIT),
        "8": ("fanmodule", State.OK),
    }
    for line in section:
        index, status, product_name = line
        if not index == item:
            continue
        state_readable, state = power_status[status]
        yield Result(state=state, summary=f"[{product_name}] Status: {state_readable}")
        return


def parse_blade_bx_powermod(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_blade_bx_powermod = SimpleSNMPSection(
    name="blade_bx_powermod",
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.2.4.1",
        oids=["1", "2", "4"],
    ),
    parse_function=parse_blade_bx_powermod,
)
check_plugin_blade_bx_powermod = CheckPlugin(
    name="blade_bx_powermod",
    service_name="Power Module %s",
    discovery_function=inventory_blade_bx_powermod,
    check_function=check_blade_bx_powermod,
)
