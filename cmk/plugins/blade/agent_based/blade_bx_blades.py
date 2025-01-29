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


def inventory_blade_bx_blades(section: StringTable) -> DiscoveryResult:
    for id_, status, _serial, _name in section:
        if status != "3":  # blade not present
            yield Service(item=id_)


def check_blade_bx_blades(item: str, section: StringTable) -> CheckResult:
    status_codes = {
        "1": (State.UNKNOWN, "unknown"),
        "2": (State.OK, "OK"),
        "3": (State.UNKNOWN, "not present"),
        "4": (State.CRIT, "error"),
        "5": (State.CRIT, "critical"),
        "6": (State.OK, "standby"),
    }

    for id_, status, serial, name in section:
        if id_ == item:
            state, state_readable = status_codes[status]
            if name:
                name_info = f"[{name}, Serial: {serial}]"
            else:
                name_info = "[Serial: %s]" % serial
            yield Result(state=state, summary=f"{name_info} Status: {state_readable}")
            return


def parse_blade_bx_blades(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_blade_bx_blades = SimpleSNMPSection(
    name="blade_bx_blades",
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.4.2.1.1",
        oids=["1", "2", "5", "21"],
    ),
    parse_function=parse_blade_bx_blades,
)
check_plugin_blade_bx_blades = CheckPlugin(
    name="blade_bx_blades",
    service_name="Blade %s",
    discovery_function=inventory_blade_bx_blades,
    check_function=check_blade_bx_blades,
)
