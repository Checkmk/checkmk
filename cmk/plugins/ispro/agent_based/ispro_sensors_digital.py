#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS

_MAP_ALARM = {
    "1": (State.OK, "normal", "active"),
    "2": (State.CRIT, "alarm", "inactive"),
}

_MAP_STATE = {
    "1": "disabled",
    "2": "normal open",
    "3": "normal close",
}

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.3.1.2.1 "Water Sensor-R" --> ISPRO-MIB::isDeviceMonitorDigitalInName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.3.1.4.1 1 --> ISPRO-MIB::isDeviceMonitorDigitalInAlarm
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.4.1.3.1 2 --> ISPRO-MIB::isDeviceConfigDigitalInState


def discover_ispro_sensors_digital(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section if line[0] and line[2] != "1")


def check_ispro_sensors_digital(item: str, section: StringTable) -> CheckResult:
    for name, alarm, state in section:
        if item == name:
            # more readable, avoiding confusion
            alarm_state, alarm_state_readable, alarm_device_state_readable = _MAP_ALARM.get(
                alarm, (State.UNKNOWN, "unknown", f"unexpected({alarm})")
            )
            state_readable = _MAP_STATE.get(state, f"unexpected({state})")
            yield Result(
                state=alarm_state,
                summary=(
                    f"Status: {state_readable}, "
                    f"Alarm status: {alarm_state_readable} (device: {alarm_device_state_readable})"
                ),
            )
            return


def parse_ispro_sensors_digital(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ispro_sensors_digital = SimpleSNMPSection(
    name="ispro_sensors_digital",
    parse_function=parse_ispro_sensors_digital,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3",
        oids=["1.3.1.2", "1.3.1.4", "2.4.1.3"],
    ),
)


check_plugin_ispro_sensors_digital = CheckPlugin(
    name="ispro_sensors_digital",
    service_name="Digital in %s",
    discovery_function=discover_ispro_sensors_digital,
    check_function=check_ispro_sensors_digital,
)
