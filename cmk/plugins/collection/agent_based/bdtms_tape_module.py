#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_bdtms_tape_module(section: StringTable) -> DiscoveryResult:
    for device in section:
        device_id = device[0]
        yield Service(item=device_id)


def check_bdtms_tape_module(item: str, section: StringTable) -> CheckResult:
    def state(status: str) -> State:
        return State.OK if status.lower() == "ok" else State.CRIT

    for device in section:
        device_id, module_status, board_status, power_status = device
        if device_id != item:
            continue

        yield Result(state=state(module_status), summary="Module: %s" % module_status.lower())
        yield Result(state=state(board_status), summary="Board: %s" % board_status.lower())
        yield Result(state=state(power_status), summary="Power supply: %s" % power_status.lower())


def parse_bdtms_tape_module(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bdtms_tape_module = SimpleSNMPSection(
    name="bdtms_tape_module",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.2.4.1",
        oids=[OIDEnd(), "4", "5", "6"],
    ),
    parse_function=parse_bdtms_tape_module,
)
check_plugin_bdtms_tape_module = CheckPlugin(
    name="bdtms_tape_module",
    service_name="Tape Library Module %s",
    discovery_function=inventory_bdtms_tape_module,
    check_function=check_bdtms_tape_module,
)
