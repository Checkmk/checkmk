#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, SimpleSNMPSection, SNMPTree
from cmk.plugins.lib.enviromux import (
    check_enviromux_humidity,
    check_enviromux_temperature,
    check_enviromux_voltage,
    DETECT_ENVIROMUX_SEMS,
    discover_enviromux_humidity,
    discover_enviromux_temperature,
    discover_enviromux_voltage,
    ENVIROMUX_CHECK_DEFAULT_PARAMETERS,
    parse_enviromux,
)

snmp_section_enviromux_sems = SimpleSNMPSection(
    name="enviromux_sems",
    parse_function=parse_enviromux,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.2.1.4.1.1",
        oids=[
            "1",  # intSensorIndex
            "2",  # intSensorType
            "3",  # intSensorDescription
            "6",  # intSensorValue
            "10",  # intSensorMinThreshold
            "11",  # intSensorMaxThreshold
        ],
    ),
    detect=DETECT_ENVIROMUX_SEMS,
)
# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


check_plugin_enviromux_sems = CheckPlugin(
    name="enviromux_sems",
    service_name="Sensor %s",
    discovery_function=discover_enviromux_temperature,
    check_function=check_enviromux_temperature,
    check_default_parameters={},
    check_ruleset_name="temperature",
)


# .
#   .--Voltage-------------------------------------------------------------.
#   |                 __     __    _ _                                     |
#   |                 \ \   / /__ | | |_ __ _  __ _  ___                   |
#   |                  \ \ / / _ \| | __/ _` |/ _` |/ _ \                  |
#   |                   \ V / (_) | | || (_| | (_| |  __/                  |
#   |                    \_/ \___/|_|\__\__,_|\__, |\___|                  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
check_plugin_enviromux_sems_voltage = CheckPlugin(
    name="enviromux_sems_voltage",
    sections=["enviromux_sems"],
    service_name="Sensor %s",
    discovery_function=discover_enviromux_voltage,
    check_function=check_enviromux_voltage,
    check_default_parameters=ENVIROMUX_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="voltage",
)


# .
#   .--Humidity------------------------------------------------------------.
#   |              _   _                 _     _ _ _                       |
#   |             | | | |_   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | |_| | | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             |  _  | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

check_plugin_enviromux_sems_humidity = CheckPlugin(
    name="enviromux_sems_humidity",
    sections=["enviromux_sems"],
    service_name="Sensor %s",
    discovery_function=discover_enviromux_humidity,
    check_function=check_enviromux_humidity,
    check_default_parameters={},
    check_ruleset_name="humidity",
)
