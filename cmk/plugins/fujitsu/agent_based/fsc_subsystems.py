#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def discover_fsc_subsystems(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section if int(line[1]) > 0)


def check_fsc_subsystems(item: str, section: StringTable) -> CheckResult:
    for line in section:
        name = line[0]
        if name != item:
            continue
        if line[1] == "":
            yield Result(state=State.UNKNOWN, summary="Status not found in SNMP data")
            return
        status = int(line[1])
        statusname = {1: "ok", 2: "degraded", 3: "error", 4: "failed", 5: "unknown-init"}.get(
            status, "invalid"
        )
        if status in {1, 5}:
            yield Result(state=State.OK, summary=f"{statusname} - no problems")
            return
        if 2 <= status <= 4:
            yield Result(state=State.CRIT, summary=f"{statusname}")
            return
        yield Result(state=State.UNKNOWN, summary=f"unknown status {status}")
        return


def parse_fsc_subsystems(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fsc_subsystems = SimpleSNMPSection(
    name="fsc_subsystems",
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
        ),
        exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.11.3.1.1",
        oids=["2", "3"],
    ),
    parse_function=parse_fsc_subsystems,
)


check_plugin_fsc_subsystems = CheckPlugin(
    name="fsc_subsystems",
    service_name="FSC %s",
    discovery_function=discover_fsc_subsystems,
    check_function=check_fsc_subsystems,
)
