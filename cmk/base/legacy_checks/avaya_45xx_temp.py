#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def discover_avaya_45xx_temp(info):
    for idx, _line in enumerate(info):
        yield str(idx), {}


def check_avaya_45xx_temp(item, params, info):
    for idx, temp in enumerate(info):
        if str(idx) == item:
            return check_temperature(float(temp[0]) / 2.0, params, "avaya_45xx_temp_%s" % item)
    return None


def parse_avaya_45xx_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["avaya_45xx_temp"] = LegacyCheckDefinition(
    name="avaya_45xx_temp",
    parse_function=parse_avaya_45xx_temp,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.45.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.45.1.6.3.7.1.1.5",
        oids=["5"],
    ),
    service_name="Temperature Chassis %s",
    discovery_function=discover_avaya_45xx_temp,
    check_function=check_avaya_45xx_temp,
    check_ruleset_name="temperature",
    # S5-CHASSIS-MIB::s5ChasTmpSnrTmpValue
    # The current temperature value of the temperature
    # sensor. This is measured in units of a half degree
    # centigrade, e.g. a value of 121 indicates a temperature
    # of 60.5 degrees C.,
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)
