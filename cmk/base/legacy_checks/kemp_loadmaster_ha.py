#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12196.13.0.9.0 1
# .1.3.6.1.4.1.12196.13.0.10.0 7.1-20b.20140926-1505


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, equals, exists, SNMPTree, StringTable

check_info = {}


def discover_kemp_loadmaster_ha(info: StringTable) -> list[tuple[None, None]]:
    if info and info[0][0] != "0":
        return [(None, None)]
    return []


def check_kemp_loadmaster_ha(
    _no_item: None, _no_params: Mapping[str, Any], info: StringTable
) -> tuple[int, str]:
    map_states = {
        "0": "none",
        "1": "master",
        "2": "standby",
        "3": "passive",
    }

    return 0, f"Device is: {map_states[info[0][0]]} (Firmware: {info[0][1]})"


def parse_kemp_loadmaster_ha(string_table: StringTable) -> StringTable:
    return string_table


check_info["kemp_loadmaster_ha"] = LegacyCheckDefinition(
    name="kemp_loadmaster_ha",
    parse_function=parse_kemp_loadmaster_ha,
    detect=all_of(
        any_of(
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12196.250.10"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2021.250.10"),
        ),
        exists(".1.3.6.1.4.1.12196.13.0.9.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12196.13.0",
        oids=["9", "10"],
    ),
    service_name="HA State",
    discovery_function=discover_kemp_loadmaster_ha,
    check_function=check_kemp_loadmaster_ha,
)
