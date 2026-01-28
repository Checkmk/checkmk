#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    DiscoveryResult,
    exists,
    not_exists,
    Service,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType

check_info = {}

# We fetch the following columns from SNMP:
# 13: name of the temperature sensor (used as item)
# 11: current temperature in C
# 6:  warning level
# 8:  critical level


def discover_fsc_temp(string_table: StringTable) -> DiscoveryResult:
    # Ignore non-connected sensors
    yield from (Service(item=line[0]) for line in string_table if int(line[1]) < 500)


def check_fsc_temp(item: str, params: TempParamType, info: StringTable) -> LegacyResult | None:
    for name, rawtemp, warn, crit in info:
        if name == item:
            temp = int(rawtemp)
            if temp in {-1, 4294967295}:
                return 3, "Sensor or component missing"

            return check_temperature(
                temp, params, "fsc_temp_%s" % item, dev_levels=(int(warn), int(crit))
            )
    return None


def parse_fsc_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["fsc_temp"] = LegacyCheckDefinition(
    name="fsc_temp",
    parse_function=parse_fsc_temp,
    detect=all_of(
        all_of(
            any_of(
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            ),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        ),
        not_exists(".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.5.2.1.1",
        oids=["13", "11", "6", "8"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_fsc_temp,
    check_function=check_fsc_temp,
    check_ruleset_name="temperature",
)
