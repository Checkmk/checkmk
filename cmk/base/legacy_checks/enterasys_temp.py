#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS

check_info = {}


def discover_enterasys_temp(info):
    if info and info[0][0] != "0":
        return [("Ambient", {})]
    return []


def check_enterasys_temp(item, params, info):
    # info for MIB: The ambient temperature of the room in which the chassis
    # is located. If this sensor is broken or not supported, then
    # this object will be set to zero. The value of this object
    # is the actual temperature in degrees Fahrenheit * 10.
    if info[0][0] == "0":
        return 3, "Sensor broken or not supported"

    # temp = fahrenheit_to_celsius(int(info[0][0]) / 10.0)
    temp = int(info[0][0]) / 10.0
    return check_temperature(temp, params, "enterasys_temp_%s" % item, dev_unit="f")


def parse_enterasys_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["enterasys_temp"] = LegacyCheckDefinition(
    name="enterasys_temp",
    parse_function=parse_enterasys_temp,
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.1.1.8.1",
        oids=["1"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_enterasys_temp,
    check_function=check_enterasys_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
