#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import startswith
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDBytes, SNMPTree


def inventory_hp_mcs_system(info):
    return [(info[0][0], None)]


def check_hp_mcs_system(item, _no_params, info):
    translate_status = {
        0: (2, "Not available"),
        1: (3, "Other"),
        2: (0, "OK"),
        3: (1, "Degraded"),
        4: (2, "Failed"),
    }
    serial = info[0][2]
    _idx1, status, _idx2, _dev_type = info[0][1]
    state, state_readable = translate_status[status]
    if state:
        yield state, "Status: %s" % state_readable
    yield 0, "Serial: %s" % serial


check_info["hp_mcs_system"] = {
    "detect": startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.232.167"),
    "discovery_function": inventory_hp_mcs_system,
    "check_function": check_hp_mcs_system,
    "service_name": "%s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.232",
        oids=["2.2.4.2", OIDBytes("11.2.10.1"), "11.2.10.3"],
    ),
}
