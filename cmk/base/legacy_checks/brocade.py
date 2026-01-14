#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# Example output from agent:
# [['1', '24', 'SLOT #0: TEMP #1'],
# ['2', '12', 'SLOT #0: TEMP #2'],
# ['3', '12', 'SLOT #0: TEMP #3'],
# ['4', '4687', 'FAN #1'],
# ['5', '4560', 'FAN #2'],
# ['6', '4821', 'FAN #3'],
# ['7', '1', 'Power Supply #1'],
# ['8', '1', 'Power Supply #2']]


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_brocade(string_table: StringTable) -> StringTable:
    return string_table


check_info["brocade"] = LegacyCheckDefinition(
    name="brocade",
    parse_function=parse_brocade,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.24.1.1588.2.1.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.2.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.3.3.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.1.22.1",
        oids=["3", "4", "5"],
    ),
)


def brocade_sensor_convert(info, what):
    return_list = []
    for presence, state, name in info:
        name = name.lstrip()  # remove leading spaces provided via SNMP
        if name.startswith(what) and presence != "6" and (saveint(state) > 0 or what == "Power"):
            sensor_id = name.split("#")[-1]
            return_list.append([sensor_id, name, state])
    return return_list


def discover_brocade_fan(info):
    converted = brocade_sensor_convert(info, "FAN")
    return [(x[0], {}) for x in converted]


def check_brocade_fan(item, params, info):
    converted = brocade_sensor_convert(info, "FAN")
    if isinstance(params, tuple):  # old format
        params = {"lower": params}

    for snmp_item, _name, value in converted:
        if item == snmp_item:
            return check_fan(int(value), params)
    return None


check_info["brocade.fan"] = LegacyCheckDefinition(
    name="brocade_fan",
    service_name="FAN %s",
    sections=["brocade"],
    discovery_function=discover_brocade_fan,
    check_function=check_brocade_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (3000, 2800)},
)


def discover_brocade_power(info):
    converted = brocade_sensor_convert(info, "Power")
    return [(x[0], None) for x in converted]


def check_brocade_power(item, _no_params, info):
    converted = brocade_sensor_convert(info, "Power")
    for snmp_item, name, value in converted:
        if item == snmp_item:
            value = int(value)
            if value != 1:
                return 2, "Error on supply %s" % name
            return 0, "No problems found"

    return 3, "Supply not found"


check_info["brocade.power"] = LegacyCheckDefinition(
    name="brocade_power",
    service_name="Power supply %s",
    sections=["brocade"],
    discovery_function=discover_brocade_power,
    check_function=check_brocade_power,
)


def discover_brocade_temp(info):
    converted = brocade_sensor_convert(info, "SLOT")
    return [(x[0], {}) for x in converted]


def check_brocade_temp(item, params, info):
    converted = brocade_sensor_convert(info, "SLOT")
    for snmp_item, _name, value in converted:
        if item == snmp_item:
            return check_temperature(int(value), params, "brocade_temp_%s" % item)
    return None


check_info["brocade.temp"] = LegacyCheckDefinition(
    name="brocade_temp",
    service_name="Temperature Ambient %s",
    sections=["brocade"],
    discovery_function=discover_brocade_temp,
    check_function=check_brocade_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (55.0, 60.0)},
)
