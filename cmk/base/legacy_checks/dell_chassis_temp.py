#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.dell.lib import DETECT_CHASSIS

check_info = {}


def discover_dell_chassis_temp(info):
    if info and len(info[0]) == 3:
        yield "Front Panel", {}
        yield "CMC Ambient", {}
        yield "CMC Processor", {}


def check_dell_chassis_temp(item, params, info):
    items = {
        "Front Panel": 0,
        "CMC Ambient": 1,
        "CMC Processor": 2,
    }

    if item in items:
        item_id = items[item]

        temp = float(info[0][item_id])
        return check_temperature(temp, params, "dell_chassis_temp_%s" % item)

    return 3, "Sensor not found in SNMP data"


def parse_dell_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_temp"] = LegacyCheckDefinition(
    name="dell_chassis_temp",
    parse_function=parse_dell_chassis_temp,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.3.1",
        oids=["10", "11", "12"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_dell_chassis_temp,
    check_function=check_dell_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (60.0, 80.0)},
)
