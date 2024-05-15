#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP data:
# .1.3.6.1.4.1.1588.2.1.1.1.1.6.0 v4.0.1    Firmware
# .1.3.6.1.4.1.1588.2.1.1.1.1.7.0 1         Status


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import all_of, any_of, equals, exists, SNMPTree, startswith, StringTable


def inventory_brocade_vdx_status(info):
    return [(None, None)]


def check_brocade_vdx_status(_no_item, _no_params, info):
    states = {
        1: "online",
        2: "offline",
        3: "testing",
        4: "faulty",
    }
    firmware = info[0][0]
    state = saveint(info[0][1])
    message = f"State: {states[state]}, Firmware: {firmware}"
    if state == 1:
        return 0, message
    if state in [2, 4]:
        return 2, message
    if state == 3:
        return 1, message
    return None


def parse_brocade_vdx_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["brocade_vdx_status"] = LegacyCheckDefinition(
    parse_function=parse_brocade_vdx_status,
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
        ),
        exists(".1.3.6.1.4.1.1588.2.1.1.1.1.6.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.1",
        oids=["6", "7"],
    ),
    service_name="Status",
    # It does not seem to work to exclude several OIDs here, there seem
    # to be too many devices which do not have the needed OIDs. We try
    # another approach: check for existance of the first needed OID
    # not oid('.1.3.6.1.2.1.1.2.0').startswith( ".1.3.6.1.4.1.1588.2.1.1.1"),
    discovery_function=inventory_brocade_vdx_status,
    check_function=check_brocade_vdx_status,
)
