#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_CHASSIS


def inventory_dell_chassis_kvm(info):
    if info:
        return [(None, None)]
    return []


def check_dell_chassis_kvm(_no_item, _no_params, info):
    state_table = {
        "1": ("other, ", 1),
        "2": ("unknown, ", 1),
        "3": ("normal", 0),
        "4": ("nonCritical, ", 1),
        "5": ("Critical, ", 2),
        "6": ("NonRecoverable, ", 2),
    }
    infotext, state = state_table.get(info[0][0], ("unknown state", 3))

    infotext = "Status: " + infotext

    infotext += ", Firmware: %s" % info[0][1]

    return state, infotext


def parse_dell_chassis_kvm(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_kvm"] = LegacyCheckDefinition(
    parse_function=parse_dell_chassis_kvm,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["3.1.2", "1.2.2"],
    ),
    service_name="Overall KVM Status",
    discovery_function=inventory_dell_chassis_kvm,
    check_function=check_dell_chassis_kvm,
)
