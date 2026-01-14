#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.avaya.lib import DETECT_AVAYA

check_info = {}


def discover_avaya_chassis_temp(info):
    if info:
        return [("Chassis", {})]
    return []


def check_avaya_chassis_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "avaya_chassis_temp_%s" % item)


def parse_avaya_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["avaya_chassis_temp"] = LegacyCheckDefinition(
    name="avaya_chassis_temp",
    parse_function=parse_avaya_chassis_temp,
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.100.1",
        oids=["2"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_avaya_chassis_temp,
    check_function=check_avaya_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)
