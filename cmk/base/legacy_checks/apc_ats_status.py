#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree


def inventory_apc_ats_status(info):
    if len(info) == 1:
        return [(None, saveint(info[0][1]))]
    return []


def check_apc_ats_status(_no_item, source, info):
    comstatus, selected_source, redundancy, overcurrent, ps5, ps24 = map(saveint, info[0])
    state = 0
    messages = []

    # current source of power
    sources = {1: "A", 2: "B"}
    if source != selected_source:
        state = 2
        messages.append(
            "Power source Changed from %s to %s(!!)" % (sources[source], sources[selected_source])
        )
    else:
        messages.append("Power source %s selected" % sources[source])

    # current communication status of the Automatic Transfer Switch.
    if comstatus == 1:
        state = max(1, state)
        messages.append("Communication Status: never Discovered(!)")
    elif comstatus == 3:
        state = 2
        messages.append("Communication Status: lost(!!)")

    # current redundancy state of the ATS.
    # Lost(1) indicates that the ATS is unable to switch over to the alternate power source
    # if the current source fails. Redundant(2) indicates that the ATS will switch
    # over to the alternate power source if the current source fails.
    if redundancy != 2:
        state = 2
        messages.append("redundancy lost(!!)")
    else:
        messages.append("Device fully redundant")

    # current state of the ATS. atsOverCurrent(1) indicates that the ATS has i
    # exceeded the output current threshold and will not allow a switch
    # over to the alternate power source if the current source fails.
    # atsCurrentOK(2) indicates that the output current is below the output current threshold.
    if overcurrent == 1:
        state = 2
        messages.append("exceedet ouput current threshold(!!)")

    # 5Volt power supply
    if ps5 != 2:
        state = 2
        messages.append("5V power supply failed(!!)")

    # 24Volt power supply
    if ps24 != 2:
        state = 2
        messages.append("24V power suppy failed(!!)")

    return state, ", ".join(messages)


check_info["apc_ats_status"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.11"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.8.5.1",
        oids=["1.0", "2.0", "3.0", "4.0", "5.0", "6.0"],
    ),
    service_name="ATS Status",
    discovery_function=inventory_apc_ats_status,
    check_function=check_apc_ats_status,
)
