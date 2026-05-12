#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDBytes,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringByteTable,
)

_STATUS_MAP: dict[int, tuple[State, str]] = {
    0: (State.CRIT, "Not available"),
    1: (State.UNKNOWN, "Other"),
    2: (State.OK, "OK"),
    3: (State.WARN, "Degraded"),
    4: (State.CRIT, "Failed"),
}


def parse_hp_mcs_system(string_table: StringByteTable) -> StringByteTable:
    return string_table


def discover_hp_mcs_system(section: StringByteTable) -> DiscoveryResult:
    if section and isinstance(name := section[0][0], str):
        yield Service(item=name)


def check_hp_mcs_system(item: str, section: StringByteTable) -> CheckResult:
    if not section:
        return
    row = section[0]
    serial = row[2]
    status_bytes = row[1]
    if not isinstance(status_bytes, list) or len(status_bytes) < 4:
        return
    _idx1, status, _idx2, _dev_type = status_bytes
    state, state_readable = _STATUS_MAP[status]
    if state is not State.OK:
        yield Result(state=state, summary=f"Status: {state_readable}")
    yield Result(state=State.OK, summary=f"Serial: {serial}")


snmp_section_hp_mcs_system = SimpleSNMPSection(
    name="hp_mcs_system",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.232.167"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232",
        oids=["2.2.4.2", OIDBytes("11.2.10.1"), "11.2.10.3"],
    ),
    parse_function=parse_hp_mcs_system,
)


check_plugin_hp_mcs_system = CheckPlugin(
    name="hp_mcs_system",
    service_name="%s",
    discovery_function=discover_hp_mcs_system,
    check_function=check_hp_mcs_system,
)
