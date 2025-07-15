#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.lib.ups_modulys import DETECT_UPS_MODULYS

check_info = {}


def parse_ups_modulys_inphase(string_table):
    if not string_table:
        return None
    parsed = {}
    parsed["Phase 1"] = {
        "frequency": int(string_table[0][1]) / 10.0,
        "voltage": int(string_table[0][2]) / 10.0,
        "current": int(string_table[0][3]) / 10.0,
    }

    if string_table[0][0] == "3":
        parsed["Phase 2"] = {
            "frequency": int(string_table[0][4]) / 10.0,
            "voltage": int(string_table[0][5]) / 10.0,
            "current": int(string_table[0][6]) / 10.0,
        }

        parsed["Phase 3"] = {
            "frequency": int(string_table[0][7]) / 10.0,
            "voltage": int(string_table[0][8]) / 10.0,
            "current": int(string_table[0][9]) / 10.0,
        }

    return parsed


def discover_ups_modulys_inphase(section):
    yield from ((item, {}) for item in section)


check_info["ups_modulys_inphase"] = LegacyCheckDefinition(
    name="ups_modulys_inphase",
    detect=DETECT_UPS_MODULYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2254.2.4.4",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    ),
    parse_function=parse_ups_modulys_inphase,
    service_name="Input %s",
    discovery_function=discover_ups_modulys_inphase,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
