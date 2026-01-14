#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, contains, endswith, exists, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# No factory default because of different defaultlevels
carel_temp_defaultlevels = {
    "Room": (30, 35),
    "Outdoor": (60, 70),
    "Delivery": (60, 70),
    "Cold Water": (60, 70),
    "Hot Water": (60, 70),
    "Cold Water Outlet": (60, 70),
    "Circuit 1 Suction": (60, 70),
    "Circuit 2 Suction": (60, 70),
    "Circuit 1 Evap": (60, 70),
    "Circuit 2 Evap": (60, 70),
    "Circuit 1 Superheat": (60, 70),
    "Circuit 2 Superheat": (60, 70),
    "Cooling Set Point": (60, 70),
    "Cooling Prop. Band": (60, 70),
    "Cooling 2nd Set Point": (60, 70),
    "Heating Set Point": (60, 70),
    "Heating 2nd Set Point": (60, 70),
    "Heating Prop. Band": (60, 70),
}


def carel_sensors_parse(string_table):
    oid_parse = {
        "1.0": "Room",
        "2.0": "Outdoor",
        "3.0": "Delivery",
        "4.0": "Cold Water",
        "5.0": "Hot Water",
        "7.0": "Cold Water Outlet",
        "10.0": "Circuit 1 Suction",
        "11.0": "Circuit 2 Suction",
        "12.0": "Circuit 1 Evap",
        "13.0": "Circuit 2 Evap",
        "14.0": "Circuit 1 Superheat",
        "15.0": "Circuit 2 Superheat",
        "20.0": "Cooling Set Point",
        "21.0": "Cooling Prop. Band",
        "22.0": "Cooling 2nd Set Point",
        "23.0": "Heating Set Point",
        "24.0": "Heating 2nd Set Point",
        "25.0": "Heating Prop. Band",
    }

    parsed = {}
    for oidend, value in string_table:
        sensor_name = oid_parse.get(oidend)
        if sensor_name is not None and value not in {None, "0", "-9999"}:
            parsed[sensor_name] = float(value) / 10

    return parsed


def discover_carel_sensors_temp(parsed):
    for sensor in parsed:
        levels = carel_temp_defaultlevels[sensor]
        yield sensor, {"levels": levels}


def check_carel_sensors_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "carel_sensors_temp_%s" % item)
    return None


check_info["carel_sensors"] = LegacyCheckDefinition(
    name="carel_sensors",
    detect=all_of(
        any_of(contains(".1.3.6.1.2.1.1.1.0", "pCO"), endswith(".1.3.6.1.2.1.1.1.0", "armv4l")),
        exists(".1.3.6.1.4.1.9839.1.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=carel_sensors_parse,
    service_name="Temperature %s",
    discovery_function=discover_carel_sensors_temp,
    check_function=check_carel_sensors_temp,
    check_ruleset_name="temperature",
)
