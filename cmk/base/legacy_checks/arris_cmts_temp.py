#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def discover_arris_cmts_temp(info):
    for line in info:
        # only devices with not default temperature
        if line[1] != "999":
            yield line[0], {}


def check_arris_cmts_temp(item, params, info):
    for name, temp in info:
        if name == item:
            return check_temperature(int(temp), params, "arris_cmts_temp_%s" % item)

    return 3, "Sensor not found in SNMP data"


def parse_arris_cmts_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["arris_cmts_temp"] = LegacyCheckDefinition(
    name="arris_cmts_temp",
    parse_function=parse_arris_cmts_temp,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.10.1.4.2.1",
        oids=["3", "29"],
    ),
    service_name="Temperature Module %s",
    discovery_function=discover_arris_cmts_temp,
    check_function=check_arris_cmts_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (40.0, 46.0)},
)
