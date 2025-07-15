#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.plugins.lib.vutlan import DETECT_VUTLAN_EMS

check_info = {}

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#
# NOTE: the unit is not given in the SNMP walk, it is %


def parse_vutlan_ems_humidity(string_table):
    parsed = {}
    for line in string_table[0]:
        if line[0].startswith("202"):
            # all OIDs 202xxx are humidity-related
            parsed[line[1]] = float(line[2])

    return parsed


def discover_vutlan_ems_humidity(parsed):
    for sensor_name in parsed:
        yield sensor_name, {}


def check_vutlan_ems_humidity(item, params, parsed):
    if not parsed.get(item):
        return

    yield check_humidity(parsed[item], params)


check_info["vutlan_ems_humidity"] = LegacyCheckDefinition(
    name="vutlan_ems_humidity",
    detect=DETECT_VUTLAN_EMS,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.39052.1.3.1",
            oids=[OIDEnd(), "7", "9"],
        )
    ],
    parse_function=parse_vutlan_ems_humidity,
    service_name="Humidity %s",
    discovery_function=discover_vutlan_ems_humidity,
    check_function=check_vutlan_ems_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 70.0),
        "levels_lower": (30.0, 15.0),
    },
)
