#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import all_of, contains, SNMPTree


def inventory_quantum_libsmall_door(info):
    return [(None, None)]


def check_quantum_libsmall_door(_no_item, _no_params, info):
    if info[0][0] == "1":
        return 2, "Library door open"
    if info[0][0] == "2":
        return 0, "Library door closed"
    return 3, "Library door status unknown"


check_info["quantum_libsmall_door"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "linux"), contains(".1.3.6.1.2.1.1.6.0", "library")
    ),
    check_function=check_quantum_libsmall_door,
    discovery_function=inventory_quantum_libsmall_door,
    service_name="Tape library door",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3697.1.10.10.1.15.2",
        oids=["0"],
    ),
)
