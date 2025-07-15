#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.lib.alcatel import DETECT_ALCATEL

check_info = {}


def parse_alcatel_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_alcatel_temp(info):
    with_slot = len(info) != 1
    for index, row in enumerate(info):
        for oid, name in enumerate(["Board", "CPU"]):
            if row[oid] != "0":
                if with_slot:
                    yield f"Slot {index + 1} {name}", {}
                else:
                    yield name, {}


def check_alcatel_temp(item, params, info):
    if len(info) == 1:
        slot_index = 0
    else:
        slot = int(item.split()[1])
        slot_index = slot - 1
    sensor = item.split()[-1]
    items = {"Board": 0, "CPU": 1}
    try:
        # If multiple switches are staked and one of them are
        # not reachable, prevent a exception
        temp_celsius = int(info[slot_index][items[sensor]])
    except Exception:
        return 3, "Sensor not found"
    return check_temperature(temp_celsius, params, "alcatel_temp_%s" % item)


check_info["alcatel_temp"] = LegacyCheckDefinition(
    name="alcatel_temp",
    parse_function=parse_alcatel_temp,
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.1.1.3.1.1.3.1",
        oids=["4", "5"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_alcatel_temp,
    check_function=check_alcatel_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (45.0, 50.0),
    },
)
