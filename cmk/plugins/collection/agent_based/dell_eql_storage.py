#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def inventory_dell_eql_storage(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_dell_eql_storage(item: str, section: StringTable) -> CheckResult:
    for (
        name,
        desc,
        health_state,
        raid_state,
        total_storage,
        repl_storage,
        snap_storage,
        used_storage,
    ) in section:
        if name == item:
            if desc:
                yield Result(state=State.OK, summary=desc)

            # Health Status:
            health_states = {
                "0": "Unknown",
                "1": "Normal",
                "2": "Warning",
                "3": "Critical",
            }
            if health_state == "1":
                state = State.OK
            elif health_state in ["2", "0"]:
                state = State.WARN
            else:
                state = State.CRIT
            yield Result(state=state, summary="Health State: %s" % health_states[health_state])

            # Raid Status
            raid_states = {
                "1": "Ok",
                "2": "Degraded",
                "3": "Verifying",
                "4": "Reconstructing",
                "5": "Failed",
                "6": "CatastrophicLoss",
                "7": "Expanding",
                "8": "Mirroring",
            }

            if raid_state == "1":
                state = State.OK
            elif raid_state in ["3", "4", "7", "8"]:
                state = State.WARN
            else:
                state = State.CRIT
            yield Result(state=state, summary="Raid State: %s" % raid_states[raid_state])

            # Storage
            total_bytes = int(total_storage) * 1048576
            used_bytes = int(used_storage) * 1048576
            repl_bytes = int(repl_storage) * 1048576
            snap_bytes = int(snap_storage) * 1048576
            yield Metric("fs_used", used_bytes)
            yield Metric("fs_used_percent", used_bytes / total_bytes * 100)
            yield Metric("fs_size", total_bytes)
            yield Metric("fs_free", total_bytes - used_bytes)
            yield Result(
                state=State.OK,
                summary=f"Used: {render.disksize(used_bytes)}/{render.disksize(total_bytes)} (Snapshots: {render.disksize(snap_bytes)}, Replication: {render.disksize(repl_bytes)})",
            )


def parse_dell_eql_storage(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_eql_storage = SimpleSNMPSection(
    name="dell_eql_storage",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "EQL-SUP"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12740.17"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12740.2.1",
        oids=[
            "1.1.9.1",
            "1.1.7.1",
            "5.1.1.1",
            "13.1.1.1",
            "10.1.1.1",
            "10.1.4.1",
            "10.1.3.1",
            "10.1.2.1",
        ],
    ),
    parse_function=parse_dell_eql_storage,
)
check_plugin_dell_eql_storage = CheckPlugin(
    name="dell_eql_storage",
    service_name="Storage %s",
    discovery_function=inventory_dell_eql_storage,
    check_function=check_dell_eql_storage,
)
