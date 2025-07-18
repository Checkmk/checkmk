#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.didactum import (
    check_didactum_sensors_humidity,
    check_didactum_sensors_temp,
    check_didactum_sensors_voltage,
    discover_didactum_sensors,
    parse_didactum_sensors,
)
from cmk.plugins.lib.didactum import DETECT_DIDACTUM

check_info = {}

# .1.3.6.1.4.1.46501.5.2.1.5.201001 Onboard Temperature --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogName.201001
# .1.3.6.1.4.1.46501.5.2.1.5.201002 Analog-1 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogName.201002
# .1.3.6.1.4.1.46501.5.2.1.5.201003 Analog-2 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogName.201003
# .1.3.6.1.4.1.46501.5.2.1.5.203001 Onboard Voltage DC --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogName.203001
# .1.3.6.1.4.1.46501.5.2.1.6.201001 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogState.201001
# .1.3.6.1.4.1.46501.5.2.1.6.201002 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogState.201002
# .1.3.6.1.4.1.46501.5.2.1.6.201003 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogState.201003
# .1.3.6.1.4.1.46501.5.2.1.6.203001 normal --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogState.203001
# .1.3.6.1.4.1.46501.5.2.1.7.201001 28.9 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogValue.201001
# .1.3.6.1.4.1.46501.5.2.1.7.201002 22.8 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogValue.201002
# .1.3.6.1.4.1.46501.5.2.1.7.201003 21.1 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogValue.201003
# .1.3.6.1.4.1.46501.5.2.1.7.203001 12.4 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogValue.203001
# .1.3.6.1.4.1.46501.5.2.1.10.201001 0.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowAlarm.201001
# .1.3.6.1.4.1.46501.5.2.1.10.201002 13.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowAlarm.201002
# .1.3.6.1.4.1.46501.5.2.1.10.201003 13.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowAlarm.201003
# .1.3.6.1.4.1.46501.5.2.1.10.203001 9.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowAlarm.203001
# .1.3.6.1.4.1.46501.5.2.1.11.201001 5.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowWarning.201001
# .1.3.6.1.4.1.46501.5.2.1.11.201002 15.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowWarning.201002
# .1.3.6.1.4.1.46501.5.2.1.11.201003 15.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowWarning.201003
# .1.3.6.1.4.1.46501.5.2.1.11.203001 11.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogLowWarning.203001
# .1.3.6.1.4.1.46501.5.2.1.12.201001 45.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighWarning.201001
# .1.3.6.1.4.1.46501.5.2.1.12.201002 27.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighWarning.201002
# .1.3.6.1.4.1.46501.5.2.1.12.201003 27.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighWarning.201003
# .1.3.6.1.4.1.46501.5.2.1.12.203001 13.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighWarning.203001
# .1.3.6.1.4.1.46501.5.2.1.13.201001 50.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighAlarm.201001
# .1.3.6.1.4.1.46501.5.2.1.13.201002 29.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighAlarm.201002
# .1.3.6.1.4.1.46501.5.2.1.13.201003 29.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighAlarm.201003
# .1.3.6.1.4.1.46501.5.2.1.13.203001 14.0 --> DIDACTUM-SYSTEM-MIB::ctlInternalSensorsAnalogHighAlarm.203001

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


def inventory_didactum_sensors_analog_temp(parsed):
    return discover_didactum_sensors(parsed, "temperature")


check_info["didactum_sensors_analog"] = LegacyCheckDefinition(
    name="didactum_sensors_analog",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.5.2.1",
        oids=["4", "5", "6", "7", "10", "11", "12", "13"],
    ),
    parse_function=parse_didactum_sensors,
    service_name="Temperature %s",
    discovery_function=inventory_didactum_sensors_analog_temp,
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


def inventory_didactum_sensors_analog_humid(parsed):
    return discover_didactum_sensors(parsed, "humidity")


check_info["didactum_sensors_analog.humidity"] = LegacyCheckDefinition(
    name="didactum_sensors_analog_humidity",
    service_name="Humidity %s",
    sections=["didactum_sensors_analog"],
    discovery_function=inventory_didactum_sensors_analog_humid,
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


def inventory_didactum_sensors_analog_volt(parsed):
    return discover_didactum_sensors(parsed, "voltage")


check_info["didactum_sensors_analog.voltage"] = LegacyCheckDefinition(
    name="didactum_sensors_analog_voltage",
    service_name="Phase %s",
    sections=["didactum_sensors_analog"],
    discovery_function=inventory_didactum_sensors_analog_volt,
    check_function=check_didactum_sensors_voltage,
    check_ruleset_name="el_inphase",
)
