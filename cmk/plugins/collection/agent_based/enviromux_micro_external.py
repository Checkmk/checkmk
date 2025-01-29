#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, SimpleSNMPSection, SNMPTree
from cmk.plugins.lib.enviromux import (
    check_enviromux_humidity,
    check_enviromux_temperature,
    DETECT_ENVIROMUX_MICRO,
    discover_enviromux_humidity,
    discover_enviromux_temperature,
    parse_enviromux_micro,
)

snmp_section_enviromux_micro_external = SimpleSNMPSection(
    name="enviromux_micro_external",
    parse_function=parse_enviromux_micro,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.12.1.2.1.1",
        oids=[
            "1",  # extSensorIndex
            "2",  # extSensorType'
            "3",  # extSensorDescription
            "4",  # extSensorValue
        ],
    ),
    detect=DETECT_ENVIROMUX_MICRO,
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


check_plugin_enviromux_micro_temperature_external = CheckPlugin(
    name="enviromux_micro_temperature_external",
    sections=["enviromux_micro_external"],
    discovery_function=discover_enviromux_temperature,
    check_function=check_enviromux_temperature,
    service_name="Sensor External %s",
    check_default_parameters={},
    check_ruleset_name="temperature",
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

check_plugin_enviromux_micro_humidity_external = CheckPlugin(
    name="enviromux_micro_humidity_external",
    sections=["enviromux_micro_external"],
    service_name="Sensor External %s",
    discovery_function=discover_enviromux_humidity,
    check_function=check_enviromux_humidity,
    check_default_parameters={},
    check_ruleset_name="humidity",
)
