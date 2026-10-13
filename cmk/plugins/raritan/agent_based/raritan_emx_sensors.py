#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


#   .--binary--------------------------------------------------------------.
#   |                   _     _                                            |
#   |                  | |__ (_)_ __   __ _ _ __ _   _                     |
#   |                  | '_ \| | '_ \ / _` | '__| | | |                    |
#   |                  | |_) | | | | | (_| | |  | |_| |                    |
#   |                  |_.__/|_|_| |_|\__,_|_|   \__, |                    |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'
from cmk.agent_based.v2 import (
    CheckPlugin,
    DiscoveryResult,
    equals,
    OIDEnd,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.raritan.lib import (
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    discover_raritan_sensors,
    parse_raritan_sensors,
    SensorSection,
)


def discover_raritan_emx_sensors(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "binary")


snmp_section_raritan_emx_sensors = SimpleSNMPSection(
    name="raritan_emx_sensors",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.8",
        oids=[
            "2.1.1.1.1",
            OIDEnd(),
            "1.2.1.1.5",
            "1.2.1.1.2",
            "2.1.1.1.2",
            "1.2.1.1.11",
            "1.2.1.1.12",
            "2.1.1.1.3",
            "1.2.1.1.20",
            "1.2.1.1.21",
            "1.2.1.1.22",
            "1.2.1.1.23",
        ],
    ),
    parse_function=parse_raritan_sensors,
)


check_plugin_raritan_emx_sensors = CheckPlugin(
    name="raritan_emx_sensors",
    service_name="Contact %s",
    discovery_function=discover_raritan_emx_sensors,
    check_function=check_raritan_sensors_binary,
)


def discover_raritan_emx_sensors_temp(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "temp")


# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

check_plugin_raritan_emx_sensors_temp = CheckPlugin(
    name="raritan_emx_sensors_temp",
    service_name="Temperature %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_temp,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_raritan_emx_sensors_airflow(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "airflow")


# .
#   .--airflow-------------------------------------------------------------.
#   |                        _       __ _                                  |
#   |                   __ _(_)_ __ / _| | _____      __                   |
#   |                  / _` | | '__| |_| |/ _ \ \ /\ / /                   |
#   |                 | (_| | | |  |  _| | (_) \ V  V /                    |
#   |                  \__,_|_|_|  |_| |_|\___/ \_/\_/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+

check_plugin_raritan_emx_sensors_airflow = CheckPlugin(
    name="raritan_emx_sensors_airflow",
    service_name="Air flow %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_airflow,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_humidity(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "humidity")


# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

check_plugin_raritan_emx_sensors_humidity = CheckPlugin(
    name="raritan_emx_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_humidity,
    check_function=check_raritan_sensors,
)


def discover_raritan_emx_sensors_pressure(section: SensorSection) -> DiscoveryResult:
    yield from discover_raritan_sensors(section, "pressure")


# .
#   .--pressure------------------------------------------------------------.
#   |                                                                      |
#   |               _ __  _ __ ___  ___ ___ _   _ _ __ ___                 |
#   |              | '_ \| '__/ _ \/ __/ __| | | | '__/ _ \                |
#   |              | |_) | | |  __/\__ \__ \ |_| | | |  __/                |
#   |              | .__/|_|  \___||___/___/\__,_|_|  \___|                |
#   |              |_|                                                     |
#   +----------------------------------------------------------------------+

check_plugin_raritan_emx_sensors_pressure = CheckPlugin(
    name="raritan_emx_sensors_pressure",
    service_name="Pressure %s",
    sections=["raritan_emx_sensors"],
    discovery_function=discover_raritan_emx_sensors_pressure,
    check_function=check_raritan_sensors,
)
