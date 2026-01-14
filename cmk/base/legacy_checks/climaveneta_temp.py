#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

climaveneta_sensors = {
    1: "Room",
    3: "Outlet Air 1",
    4: "Outlet Air 2",
    5: "Outlet Air 3",
    6: "Outlet Air 4",
    7: "Intlet Air 1",
    8: "Intlet Air 2",
    9: "Intlet Air 3",
    10: "Intlet Air 4",
    11: "Coil 1 Inlet Water",
    12: "Coil 2 Inlet Water",
    13: "Coil 1 Outlet Water",
    14: "Coil 2 Outlet Water",
    23: "Regulation Valve/Compressor",
    24: "Regulation Fan 1",
    25: "Regulation Fan 2",
    28: "Suction",
}


def discover_climaveneta_temp(info):
    for sensor_id, value in info:
        sensor_id = int(sensor_id.split(".")[0])
        if sensor_id in climaveneta_sensors and int(value) > 0:
            yield climaveneta_sensors[sensor_id], {}


def check_climaveneta_temp(item, params, info):
    for sensor_id, sensor_value in info:
        sensor_id = int(sensor_id.split(".")[0])
        if climaveneta_sensors.get(sensor_id) == item:
            sensor_value = int(sensor_value) / 10.0
            return check_temperature(sensor_value, params, "climaveneta_temp_%s" % item)
    return None


def parse_climaveneta_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["climaveneta_temp"] = LegacyCheckDefinition(
    name="climaveneta_temp",
    parse_function=parse_climaveneta_temp,
    detect=equals(".1.3.6.1.2.1.1.1.0", "pCO Gateway"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9839.2.1",
        oids=[OIDEnd(), "2"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_climaveneta_temp,
    check_function=check_climaveneta_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (28.0, 30.0)},
)
