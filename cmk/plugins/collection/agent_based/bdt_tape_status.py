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


def inventory_bdt_tape_status(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bdt_tape_status(section: StringTable) -> CheckResult:
    status_id = section[0][0]

    status = {
        "1": "other",
        "2": "unknown",
        "3": "ok",
        "4": "non-critical",
        "5": "critical",
        "6": "non-recoverable",
    }.get(status_id, "unknown")

    state = {
        "other": State.UNKNOWN,
        "unknown": State.UNKNOWN,
        "ok": State.OK,
        "non-critical": State.WARN,
        "critical": State.CRIT,
        "non-recoverable": State.CRIT,
    }.get(status, State.UNKNOWN)

    yield Result(state=state, summary=status)


def parse_bdt_tape_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_bdt_tape_status = SimpleSNMPSection(
    name="bdt_tape_status",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.10893.2.101"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.10893.2.101.2",
        oids=["1"],
    ),
    parse_function=parse_bdt_tape_status,
)
check_plugin_bdt_tape_status = CheckPlugin(
    name="bdt_tape_status",
    service_name="Tape Library Status",
    discovery_function=inventory_bdt_tape_status,
    check_function=check_bdt_tape_status,
)
