#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.vutlan import DETECT_VUTLAN_EMS

check_info = {}


def parse_vutlan_ems_leakage(string_table):
    parsed = {}
    for line in string_table[0]:
        if line[0].startswith("107"):
            # all OIDs 107xxx are leakage-related
            parsed[line[1]] = bool(int(line[2]))

    return parsed


def discover_vutlan_ems_leakage(parsed):
    for sensor_name in parsed:
        yield sensor_name, {}


def check_vutlan_ems_leakage(item, _no_params, parsed):
    if parsed.get(item) is None:
        return

    leakage_detected = bool(int(parsed[item]))
    if leakage_detected:
        yield 2, "Leak detected"
        return

    yield 0, "No leak detected"


check_info["vutlan_ems_leakage"] = LegacyCheckDefinition(
    name="vutlan_ems_leakage",
    detect=DETECT_VUTLAN_EMS,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.39052.1.3.1",
            oids=[OIDEnd(), "7", "9"],
        )
    ],
    parse_function=parse_vutlan_ems_leakage,
    service_name="Leakage %s",
    discovery_function=discover_vutlan_ems_leakage,
    check_function=check_vutlan_ems_leakage,
)
