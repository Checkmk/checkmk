#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, startswith

# Check originally developed for:
# Arista Networks EOS version 4.20.9M running on an Arista Networks DCS-7280QR-C36

# .1.3.6.1.2.1.47.1.1.1.1.2.100006001 Cpu temp sensor --> ENTITY-MIB::entPhysicalDescr.100006001
# .1.3.6.1.2.1.47.1.1.1.1.2.100006002 Cpu board temp sensor --> ENTITY-MIB::entPhysicalDescr.100006002
# .1.3.6.1.2.1.47.1.1.1.1.2.100006003 Back-panel temp sensor --> ENTITY-MIB::entPhysicalDescr.100006003
# .1.3.6.1.2.1.47.1.1.1.1.2.100006005 Front-panel temp sensor --> ENTITY-MIB::entPhysicalDescr.100006005

# .1.3.6.1.2.1.99.1.1.1.3.100006001 1 --> ENTITY-SENSOR-MIB::entPhySensorPrecision.100006001
# .1.3.6.1.2.1.99.1.1.1.3.100006002 1 --> ENTITY-SENSOR-MIB::entPhySensorPrecision.100006002
# .1.3.6.1.2.1.99.1.1.1.3.100006003 1 --> ENTITY-SENSOR-MIB::entPhySensorPrecision.100006003
# .1.3.6.1.2.1.99.1.1.1.3.100006005 1 --> ENTITY-SENSOR-MIB::entPhySensorPrecision.100006005

# .1.3.6.1.2.1.99.1.1.1.4.100006001 568 --> ENTITY-SENSOR-MIB::entPhySensorValue.100006001
# .1.3.6.1.2.1.99.1.1.1.4.100006002 470 --> ENTITY-SENSOR-MIB::entPhySensorValue.100006002
# .1.3.6.1.2.1.99.1.1.1.4.100006003 450 --> ENTITY-SENSOR-MIB::entPhySensorValue.100006003
# .1.3.6.1.2.1.99.1.1.1.4.100006004 390 --> ENTITY-SENSOR-MIB::entPhySensorValue.100006004
# .1.3.6.1.2.1.99.1.1.1.4.100006006 570 --> ENTITY-SENSOR-MIB::entPhySensorValue.100006006


def parse_arista_temp(string_table):
    parsed = {}
    for sensor, precision, value in string_table:
        if value and "temp" in sensor.lower():
            try:
                parsed[sensor] = int(value) * float("1e-%s" % precision)
            except ValueError:
                pass
    return parsed


def check_arista_temp(item, params, parsed):
    if (value := parsed.get(item)) is None:
        return
    yield check_temperature(value, params, "temp")


def discover_arista_temp(section):
    yield from ((item, {}) for item in section)


check_info["arista_temp"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "arista networks"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1",
        oids=["47.1.1.1.1.2", "99.1.1.1.3", "99.1.1.1.4"],
    ),
    parse_function=parse_arista_temp,
    service_name="Temperature %s",
    discovery_function=discover_arista_temp,
    check_function=check_arista_temp,
    check_ruleset_name="temperature",
)
