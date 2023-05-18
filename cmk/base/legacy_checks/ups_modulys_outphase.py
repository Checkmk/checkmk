#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups_modulys import DETECT_UPS_MODULYS


def parse_ups_modulys_outphase(info):
    parsed = {}
    parsed["Phase 1"] = {
        "frequency": int(info[0][1]) / 10.0,
        "voltage": int(info[0][3]) / 10.0,
        "current": int(info[0][4]) / 10.0,
        "power": int(info[0][5]),
        "output_load": int(info[0][6]),
    }

    if info[0][2] == "3":
        parsed["Phase 2"] = {
            "frequency": int(info[0][1]) / 10.0,
            "voltage": int(info[0][7]) / 10.0,
            "current": int(info[0][8]) / 10.0,
            "power": int(info[0][9]),
            "output_load": int(info[0][10]),
        }

        parsed["Phase 3"] = {
            "frequency": int(info[0][1]) / 10.0,
            "voltage": int(info[0][11]) / 10.0,
            "current": int(info[0][12]) / 10.0,
            "power": int(info[0][13]),
            "output_load": int(info[0][14]),
        }

    return parsed


check_info["ups_modulys_outphase"] = LegacyCheckDefinition(
    detect=DETECT_UPS_MODULYS,
    parse_function=parse_ups_modulys_outphase,
    discovery_function=discover(),
    check_function=check_elphase,
    service_name="Output %s",
    check_ruleset_name="ups_outphase",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2254.2.4.5",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
    ),
    check_default_parameters={},
)
