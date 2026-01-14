#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.2.0 Sys-1   # system name
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.3.0 21C     # current temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.4.0 22C     # maximum temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.5.0 18C     # minimum temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.6.0 2       # Over temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.7.0 57C     # temperature threshold
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.9.0 17      # average temperature


def discover_hp_procurve_temp(info):
    if len(info) == 1:
        return [(info[0][0], {})]
    return []


def check_hp_procurve_temp(item, params, info):
    if len(info) == 1:
        temp, dev_unit = int(info[0][1][:-1]), info[0][1][-1].lower()
        return check_temperature(temp, params, "hp_procurve_temp_%s" % item, dev_unit)
    return None


def parse_hp_procurve_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_procurve_temp"] = LegacyCheckDefinition(
    name="hp_procurve_temp",
    parse_function=parse_hp_procurve_temp,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11.2.3.7.11"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.1.2.8.1.1",
        oids=["2", "3"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_hp_procurve_temp,
    check_function=check_hp_procurve_temp,
    check_ruleset_name="temperature",
)
