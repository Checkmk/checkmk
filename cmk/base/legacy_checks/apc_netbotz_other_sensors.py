#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Max. eigth sensors
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.399845582 Wasserstand_FG1
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.3502248167 Ethernet Link Status
# .1.3.6.1.4.1.5528.100.4.2.10.1.4.3823829717 A-Link Bus Power
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.399845582 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.3502248167 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.3.3823829717 0
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.399845582 No Leak
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.3502248167 Up
# .1.3.6.1.4.1.5528.100.4.2.10.1.7.3823829717 OK


# MIB: The sensor reading shown as a string (or empty string
# if it is not plugged into a port).


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, startswith, StringTable


def inventory_apc_netbotz_other_sensors(info):
    for _sensor_label, _error_state, state_readable in info:
        if state_readable != "":
            return [(None, None)]
    return []


def check_apc_netbotz_other_sensors(_no_item, _no_params, info):
    count_ok_sensors = 0
    for sensor_label, error_state, state_readable in info:
        if state_readable != "":
            if state_readable != "OK":
                state_readable = state_readable.lower()

            if error_state == "0":
                count_ok_sensors += 1
            else:
                yield 2, f"{sensor_label}: {state_readable}"

    if count_ok_sensors > 0:
        yield 0, "%d sensors are OK" % count_ok_sensors


def parse_apc_netbotz_other_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_netbotz_other_sensors"] = LegacyCheckDefinition(
    parse_function=parse_apc_netbotz_other_sensors,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5528.100.20.10"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5528.100.4.2.10.1",
        oids=["4", "3", "7"],
    ),
    service_name="Numeric sensors summary",
    discovery_function=inventory_apc_netbotz_other_sensors,
    check_function=check_apc_netbotz_other_sensors,
)
