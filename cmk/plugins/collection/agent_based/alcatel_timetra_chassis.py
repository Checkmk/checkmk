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


def inventory_alcatel_timetra_chassis(section: StringTable) -> DiscoveryResult:
    for name, _adminstate, operstate, _alarmstate in section:
        # Only add active devices
        if operstate in ["2", "8"]:
            yield Service(item=name)


def check_alcatel_timetra_chassis(item: str, section: StringTable) -> CheckResult:
    admin_states = {
        1: (State.OK, "noop"),
        2: (State.OK, "in service"),
        3: (State.WARN, "out of service"),
        4: (State.CRIT, "diagnose"),
        5: (State.CRIT, "operate switch"),
    }

    oper_states = {
        1: (State.UNKNOWN, "unknown"),
        2: (State.OK, "in service"),
        3: (State.CRIT, "out of service"),
        4: (State.WARN, "diagnosing"),
        5: (State.CRIT, "failed"),
        6: (State.WARN, "booting"),
        7: (State.UNKNOWN, "empty"),
        8: (State.OK, "provisioned"),
        9: (State.UNKNOWN, "unprovisioned"),
        10: (State.WARN, "upgrade"),
        11: (State.WARN, "downgrade"),
        12: (State.WARN, "in service upgrade"),
        13: (State.WARN, "in service downgrade"),
        14: (State.WARN, "reset pending"),
    }

    alarm_states = {
        0: (State.OK, "unknown"),
        1: (State.CRIT, "alarm active"),
        2: (State.OK, "alarm cleared"),
    }
    for line in section:
        if line[0] == item:
            adminstate, operstate, alarmstate = map(int, line[1:])
            if operstate != adminstate:
                yield Result(
                    state=admin_states[adminstate][0],
                    notice="Admin state: %s" % admin_states[adminstate][1],
                )

            yield Result(
                state=oper_states[operstate][0],
                summary="Operational state: %s" % oper_states[operstate][1],
            )

            yield Result(
                state=alarm_states[alarmstate][0],
                notice="Alarm state: %s" % alarm_states[alarmstate][1],
            )
            return


def parse_alcatel_timetra_chassis(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_alcatel_timetra_chassis = SimpleSNMPSection(
    name="alcatel_timetra_chassis",
    detect=contains(".1.3.6.1.2.1.1.1.0", "TiMOS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6527.3.1.2.2.1.8.1",
        oids=["8", "15", "16", "24"],
    ),
    parse_function=parse_alcatel_timetra_chassis,
)
check_plugin_alcatel_timetra_chassis = CheckPlugin(
    name="alcatel_timetra_chassis",
    service_name="Device %s",
    discovery_function=inventory_alcatel_timetra_chassis,
    check_function=check_alcatel_timetra_chassis,
)
