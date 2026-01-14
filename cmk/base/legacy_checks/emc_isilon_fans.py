#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.emc.lib import DETECT_ISILON

check_info = {}


# Examples for sensor names:
# Chassis Fan1 (ISI F1) --> Chassis 1
# Chassis Fan2 (ISI F2)
# Chassis Fan3 (ISI F3)
# Power Supply 1 Fan1 --> Power Supply 1 1
# Power Supply 2 Fan1
def isilon_fan_item_name(sensor_name):
    return sensor_name.replace("Fan", "").split("(")[0].strip()


def discover_emc_isilon_fans(info):
    for fan_name, _value in info:
        yield isilon_fan_item_name(fan_name), {}


def check_emc_isilon_fans(item, params, info):
    for fan_name, value in info:
        if item == isilon_fan_item_name(fan_name):
            return check_fan(float(value), params)
    return None


def parse_emc_isilon_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["emc_isilon_fans"] = LegacyCheckDefinition(
    name="emc_isilon_fans",
    parse_function=parse_emc_isilon_fans,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.53.1",
        oids=["3", "4"],
    ),
    service_name="Fan %s",
    discovery_function=discover_emc_isilon_fans,
    check_function=check_emc_isilon_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (3000, 2500)},
)
