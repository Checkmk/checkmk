#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}


def discover_f5_bigip_chassis_temp(info):
    for line in info:
        yield line[0], {}


def check_f5_bigip_chassis_temp(item, params, info):
    for name, temp in info:
        if name == item:
            return check_temperature(int(temp), params, "f5_bigip_chassis_temp_%s" % item)
    return None


def parse_f5_bigip_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["f5_bigip_chassis_temp"] = LegacyCheckDefinition(
    name="f5_bigip_chassis_temp",
    parse_function=parse_f5_bigip_chassis_temp,
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.3.2.3.2.1",
        oids=["1", "2"],
    ),
    service_name="Temperature Chassis %s",
    discovery_function=discover_f5_bigip_chassis_temp,
    check_function=check_f5_bigip_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
