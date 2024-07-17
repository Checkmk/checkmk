#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_bdtms_tape_info(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bdtms_tape_info(section: StringTable) -> CheckResult:
    _activity_id, health_id = section[0]

    health = {
        "1": "unknown",
        "2": "ok",
        "3": "warning",
        "4": "critical",
    }.get(health_id, "unknown")

    status = {
        "unknown": State.UNKNOWN,
        "ok": State.OK,
        "warning": State.WARN,
        "critical": State.CRIT,
    }.get(health, State.UNKNOWN)

    yield Result(state=status, summary=health)


def parse_bdtms_tape_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_bdtms_tape_status = SimpleSNMPSection(
    name="bdtms_tape_status",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.2",
        oids=["1", "3"],
    ),
    parse_function=parse_bdtms_tape_status,
)
check_plugin_bdtms_tape_status = CheckPlugin(
    name="bdtms_tape_status",
    service_name="Tape Library Status",
    discovery_function=inventory_bdtms_tape_info,
    check_function=check_bdtms_tape_info,
)
