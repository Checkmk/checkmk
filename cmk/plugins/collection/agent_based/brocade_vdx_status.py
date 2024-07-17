#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP data:
# .1.3.6.1.4.1.1588.2.1.1.1.1.6.0 v4.0.1    Firmware
# .1.3.6.1.4.1.1588.2.1.1.1.1.7.0 1         Status


from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def inventory_brocade_vdx_status(section: StringTable) -> DiscoveryResult:
    yield Service()


_VDX_STATUS_MAP = {
    1: State.OK,
    2: State.CRIT,
    3: State.WARN,
    4: State.CRIT,
}

_VDX_STATUS_READABLE = {
    1: "online",
    2: "offline",
    3: "testing",
    4: "faulty",
}


def check_brocade_vdx_status(section: StringTable) -> CheckResult:
    firmware = section[0][0]
    state = int(section[0][1])

    yield Result(state=_VDX_STATUS_MAP[state], summary=f"State: {_VDX_STATUS_READABLE[state]}")
    yield Result(state=State.OK, summary=f"Firmware: {firmware}")


def parse_brocade_vdx_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_brocade_vdx_status = SimpleSNMPSection(
    name="brocade_vdx_status",
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
        ),
        exists(".1.3.6.1.4.1.1588.2.1.1.1.1.6.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.1",
        oids=["6", "7"],
    ),
    parse_function=parse_brocade_vdx_status,
)
check_plugin_brocade_vdx_status = CheckPlugin(
    name="brocade_vdx_status",
    service_name="Status",
    discovery_function=inventory_brocade_vdx_status,
    check_function=check_brocade_vdx_status,
)
