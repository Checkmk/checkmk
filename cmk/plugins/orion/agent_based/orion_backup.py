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
    startswith,
    State,
    StringTable,
)


def parse_orion_backup(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_orion_backup = SimpleSNMPSection(
    name="orion_backup",
    parse_function=parse_orion_backup,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.5.3.3",
        oids=["2", "3"],
    ),
)


def discover_orion_backup(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_orion_backup(section: StringTable) -> CheckResult:
    map_states: dict[str, tuple[State, str]] = {
        "1": (State.WARN, "inactive"),
        "2": (State.OK, "OK"),
        "3": (State.WARN, "occured"),
        "4": (State.CRIT, "fail"),
    }

    backup_time_status, backup_time = section[0]
    state, state_readable = map_states[backup_time_status]
    yield Result(
        state=state, summary=f"Status: {state_readable}, Expected time: {backup_time} minutes"
    )


check_plugin_orion_backup = CheckPlugin(
    name="orion_backup",
    service_name="Backup",
    discovery_function=discover_orion_backup,
    check_function=check_orion_backup,
)
