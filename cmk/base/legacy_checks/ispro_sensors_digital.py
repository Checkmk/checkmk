#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS

check_info = {}

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.3.1.2.1 "Water Sensor-R" --> ISPRO-MIB::isDeviceMonitorDigitalInName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.3.1.4.1 1 --> ISPRO-MIB::isDeviceMonitorDigitalInAlarm
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.4.1.3.1 2 --> ISPRO-MIB::isDeviceConfigDigitalInState


def discover_ispro_sensors_digital(info):
    return [(line[0], None) for line in info if line[0] and line[2] != "1"]


def check_ispro_sensors_digital(item, params, info):
    map_alarm = {
        "1": (0, "normal", "active"),
        "2": (2, "alarm", "inactive"),
    }
    map_state = {
        "1": "disabled",
        "2": "normal open",
        "3": "normal close",
    }

    for name, alarm, state in info:
        if item == name:
            # more readable, avoiding confusion
            alarm_state, alarm_state_readable, alarm_device_state_readable = map_alarm.get(
                alarm, (3, "unknown", "unexpected(%s)" % alarm)
            )
            return alarm_state, "Status: {}, Alarm status: {} (device: {})".format(
                map_state.get(state, "unexpected(%s)" % state),
                alarm_state_readable,
                alarm_device_state_readable,
            )
    return None


def parse_ispro_sensors_digital(string_table: StringTable) -> StringTable:
    return string_table


check_info["ispro_sensors_digital"] = LegacyCheckDefinition(
    name="ispro_sensors_digital",
    parse_function=parse_ispro_sensors_digital,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3",
        oids=["1.3.1.2", "1.3.1.4", "2.4.1.3"],
    ),
    service_name="Digital in %s",
    discovery_function=discover_ispro_sensors_digital,
    check_function=check_ispro_sensors_digital,
)
