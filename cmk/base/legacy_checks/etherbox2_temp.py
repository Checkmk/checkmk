#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, equals, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# .1.3.6.1.4.1.14848.2.1.7.1.2.1 -0.0008 Volt --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.1
# .1.3.6.1.4.1.14848.2.1.7.1.2.2 -0.0008 Volt --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.2
# .1.3.6.1.4.1.14848.2.1.7.1.2.3 5.0015 Volt  --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.3
# .1.3.6.1.4.1.14848.2.1.7.1.2.4 2.0031 Volt  --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.4
# .1.3.6.1.4.1.14848.2.1.7.1.2.5 -0.0005 Volt --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.5
# .1.3.6.1.4.1.14848.2.1.7.1.2.6 -0.0004 Volt --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.6
# .1.3.6.1.4.1.14848.2.1.7.1.2.7 5.0002 Volt  --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.7
# .1.3.6.1.4.1.14848.2.1.7.1.2.8 2.0010 Volt  --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.7.1.2.8

# .1.3.6.1.4.1.14848.2.1.9.1.2.1 -2472        --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.9.1.2.1
# .1.3.6.1.4.1.14848.2.1.9.1.2.2 252          --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.9.1.2.2
# .1.3.6.1.4.1.14848.2.1.9.1.2.3 0            --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.9.1.2.3
# .1.3.6.1.4.1.14848.2.1.9.1.2.4 248          --> BETTER-NETWORKS-ETHERNETBOX-MIB::ethernetboxObjects.9.1.2.4

# suggested by customer


def parse_etherbox2_temp(string_table):
    # We have to use xxx.7.1.2.a to know if a temperature sensor
    # is connected:
    # - if oid(xxx.7.1.2.{a}) == 5.fff and oid(xxx.7.1.2.{a+1}) == 2.fff
    #   then a temperature sensor is connected to oid(xxx.9.1.2.{(a+1)/2})
    #   (a = 1, 3, 5, ...)
    # - otherwise there's no sensor connected.
    # Furthermore we cannot only use xxx.9.1.2.{a} < 0 (or something like that)
    # because the temperature can drop below 0.
    parsed = {}
    sensor_indicators, sensors = string_table
    for sensor_index, sensor in enumerate(sensors):
        indicator_index = 2 * sensor_index
        if (
            float((sensor_indicators[indicator_index][0].split("Volt")[0]).strip()) > 4
            and float((sensor_indicators[indicator_index + 1][0].split("Volt")[0]).strip()) > 1
        ):
            parsed["Sensor %s" % sensor[0]] = float(sensor[1]) / 10

    return parsed


def discover_etherbox2_temp(parsed):
    return [(sensor, {}) for sensor in parsed]


def check_etherbox2_temp(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item], params, "etherbox2_%s" % item)
    return None


check_info["etherbox2_temp"] = LegacyCheckDefinition(
    name="etherbox2_temp",
    detect=all_of(
        equals(".1.3.6.1.2.1.1.1.0", ""), contains(".1.3.6.1.4.1.14848.2.1.1.1.0", "Version 1.2")
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.14848.2.1.7.1",
            oids=["2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.14848.2.1.9.1",
            oids=[OIDEnd(), "2"],
        ),
    ],
    parse_function=parse_etherbox2_temp,
    service_name="Temperature %s",
    discovery_function=discover_etherbox2_temp,
    check_function=check_etherbox2_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)
