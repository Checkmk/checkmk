#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, OIDBytes, Service, SNMPTree, startswith, StringTable

check_info = {}


def discover_hp_mcs_system(section: StringTable) -> DiscoveryResult:
    if not section:
        return
    yield Service(item=section[0][0])


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


def parse_hp_mcs_system(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_mcs_system"] = LegacyCheckDefinition(
    name="hp_mcs_system",
    parse_function=parse_hp_mcs_system,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.232.167"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232",
        oids=["2.2.4.2", OIDBytes("11.2.10.1"), "11.2.10.3"],
    ),
    service_name="%s",
    discovery_function=discover_hp_mcs_system,
    check_function=check_hp_mcs_system,
)
