#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# example output
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.1 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.2 8
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.3 7
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.1 Temperature In
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.2 Warning message
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.3 Alarm message
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.1 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.2 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.3 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.5.1 20
# .1.3.6.1.4.1.232.167.2.4.5.2.1.5.2 0
# .1.3.6.1.4.1.232.167.2.4.5.2.1.5.3 0
# .1.3.6.1.4.1.232.167.2.4.5.2.1.6.1 35
# .1.3.6.1.4.1.232.167.2.4.5.2.1.6.2 0
# .1.3.6.1.4.1.232.167.2.4.5.2.1.6.3 0
# .1.3.6.1.4.1.232.167.2.4.5.2.1.7.1 10
# .1.3.6.1.4.1.232.167.2.4.5.2.1.7.2 0
# .1.3.6.1.4.1.232.167.2.4.5.2.1.7.3 0


def parse_hp_mcs_sensors(string_table):
    parsed = {}

    for line in string_table:
        parsed[line[0]] = {
            "type": int(line[1]),
            "name": line[2],
            "status": int(line[3]),
            "value": float(line[4]),
            "high": float(line[5]),
            "low": float(line[6]),
        }

    return parsed


def discover_hp_mcs_sensors(parsed):
    for entry in parsed.values():
        if int(entry["type"]) in [4, 5, 13, 14, 15, 16, 17, 18, 19, 20]:
            yield (entry["name"], {})


def check_hp_mcs_sensors(item, params, parsed):
    for key, entry in parsed.items():
        if entry["name"] == item:
            return check_temperature(entry["value"], params, "hp_mcs_sensors_%s" % key)
    return None


check_info["hp_mcs_sensors"] = LegacyCheckDefinition(
    name="hp_mcs_sensors",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.232.167"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.167.2.4.5.2.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_hp_mcs_sensors,
    service_name="Sensor %s",
    discovery_function=discover_hp_mcs_sensors,
    check_function=check_hp_mcs_sensors,
    check_ruleset_name="temperature",
)


def discover_hp_mcs_sensors_fan(parsed):
    for entry in parsed.values():
        if entry["type"] in [9, 10, 11, 26, 27, 28]:
            yield (entry["name"], {})


def check_hp_mcs_sensors_fan(item, params, parsed):
    for entry in parsed.values():
        if entry["name"] == item:
            return check_fan(entry["value"], params)
    return None


check_info["hp_mcs_sensors.fan"] = LegacyCheckDefinition(
    name="hp_mcs_sensors_fan",
    service_name="Sensor %s",
    sections=["hp_mcs_sensors"],
    discovery_function=discover_hp_mcs_sensors_fan,
    check_function=check_hp_mcs_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1000, 500),
    },
)
