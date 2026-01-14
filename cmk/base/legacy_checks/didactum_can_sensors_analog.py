#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.didactum import (
    check_didactum_sensors_humidity,
    check_didactum_sensors_temp,
    check_didactum_sensors_voltage,
    discover_didactum_sensors,
    parse_didactum_sensors,
)
from cmk.plugins.didactum.lib import DETECT_DIDACTUM

check_info = {}

# .1.3.6.1.4.1.46501.6.2.1.5.201007 alpha-bravo_doppelboden_frischluft --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogName.201007
# .1.3.6.1.4.1.46501.6.2.1.6.201007 normal --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogState.201007
# .1.3.6.1.4.1.46501.6.2.1.7.201007 14.9 --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogValue.201007

#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                              main check                              |
#   '----------------------------------------------------------------------'


def discover_didactum_can_sensors_analog_temp(parsed):
    return discover_didactum_sensors(parsed, "temperature")


check_info["didactum_can_sensors_analog"] = LegacyCheckDefinition(
    name="didactum_can_sensors_analog",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.6.2.1",
        oids=["4", "5", "6", "7", "10", "11", "12", "13"],
    ),
    parse_function=parse_didactum_sensors,
    service_name="Temperature CAN %s",
    discovery_function=discover_didactum_can_sensors_analog_temp,
    check_function=check_didactum_sensors_temp,
    check_ruleset_name="temperature",
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_didactum_can_sensors_analog_humid(parsed):
    return discover_didactum_sensors(parsed, "humidity")


check_info["didactum_can_sensors_analog.humidity"] = LegacyCheckDefinition(
    name="didactum_can_sensors_analog_humidity",
    service_name="Humidity CAN %s",
    sections=["didactum_can_sensors_analog"],
    discovery_function=discover_didactum_can_sensors_analog_humid,
    check_function=check_didactum_sensors_humidity,
    check_ruleset_name="humidity",
)

# .
#   .--voltage-------------------------------------------------------------.
#   |                             _ _                                      |
#   |                 __   _____ | | |_ __ _  __ _  ___                    |
#   |                 \ \ / / _ \| | __/ _` |/ _` |/ _ \                   |
#   |                  \ V / (_) | | || (_| | (_| |  __/                   |
#   |                   \_/ \___/|_|\__\__,_|\__, |\___|                   |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


def discover_didactum_can_sensors_analog_volt(parsed):
    return discover_didactum_sensors(parsed, "voltage")


check_info["didactum_can_sensors_analog.voltage"] = LegacyCheckDefinition(
    name="didactum_can_sensors_analog_voltage",
    service_name="Phase CAN %s",
    sections=["didactum_can_sensors_analog"],
    discovery_function=discover_didactum_can_sensors_analog_volt,
    check_function=check_didactum_sensors_voltage,
    check_ruleset_name="el_inphase",
)
