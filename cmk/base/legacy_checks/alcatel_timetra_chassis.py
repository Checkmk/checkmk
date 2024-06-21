#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree, StringTable


def inventory_alcatel_timetra_chassis(info):
    for name, _adminstate, operstate, _alarmstate in info:
        # Only add active devices
        if operstate in ["2", "8"]:
            yield name, None


def check_alcatel_timetra_chassis(item, _no_params, info):
    admin_states = {
        1: (0, "noop"),
        2: (0, "in service"),
        3: (1, "out of service"),
        4: (2, "diagnose"),
        5: (2, "operate switch"),
    }

    oper_states = {
        1: (3, "unknown"),
        2: (0, "in service"),
        3: (2, "out of service"),
        4: (1, "diagnosing"),
        5: (2, "failed"),
        6: (1, "booting"),
        7: (3, "empty"),
        8: (0, "provisioned"),
        9: (3, "unprovisioned"),
        10: (1, "upgrade"),
        11: (1, "downgrade"),
        12: (1, "in service upgrade"),
        13: (1, "in service downgrade"),
        14: (1, "reset pending"),
    }

    alarm_states = {
        0: (0, "unknown"),
        1: (2, "alarm active"),
        2: (0, "alarm cleared"),
    }
    for line in info:
        if line[0] == item:
            adminstate, operstate, alarmstate = map(int, line[1:])
            if operstate != adminstate:
                if admin_states[adminstate][0] != 0:
                    yield admin_states[adminstate][0], "Admin state: %s" % admin_states[adminstate][
                        1
                    ]

            yield oper_states[operstate][0], "Operational state: %s" % oper_states[operstate][1]

            if alarm_states[alarmstate][0] != 0:
                yield alarm_states[alarmstate][0], "Alarm state: %s" % alarm_states[alarmstate][1]
            return


def parse_alcatel_timetra_chassis(string_table: StringTable) -> StringTable:
    return string_table


check_info["alcatel_timetra_chassis"] = LegacyCheckDefinition(
    parse_function=parse_alcatel_timetra_chassis,
    detect=contains(".1.3.6.1.2.1.1.1.0", "TiMOS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6527.3.1.2.2.1.8.1",
        oids=["8", "15", "16", "24"],
    ),
    service_name="Device %s",
    discovery_function=inventory_alcatel_timetra_chassis,
    check_function=check_alcatel_timetra_chassis,
)
