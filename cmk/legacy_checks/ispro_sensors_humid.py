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
    StringTable,
)
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS, sensors_alarm_states
from cmk.plugins.lib.humidity import check_humidity, CheckParams

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.2.1 "Humidity-R" --> ISPRO-MIB::isDeviceMonitorHumidityName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.3.1 4407 --> ISPRO-MIB::isDeviceMonitorHumidity
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.4.1 3 --> ISPRO-MIB::isDeviceMonitorHumidityAlarm


def discover_ispro_sensors_humid(section: StringTable) -> DiscoveryResult:
    yield from (
        Service(item=name) for name, _reading_str, status in section if status not in ["1", "2"]
    )


def check_ispro_sensors_humid(item: str, params: CheckParams, section: StringTable) -> CheckResult:
    for name, reading_str, status in section:
        if item == name:
            devstatus, devstatus_name = sensors_alarm_states(status)
            yield Result(state=devstatus, summary=f"Device status: {devstatus_name}")
            yield from check_humidity(float(reading_str) / 100.0, params)


def parse_ispro_sensors_humid(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ispro_sensors_humid = SimpleSNMPSection(
    name="ispro_sensors_humid",
    parse_function=parse_ispro_sensors_humid,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1",
        oids=["2", "3", "4"],
    ),
)


check_plugin_ispro_sensors_humid = CheckPlugin(
    name="ispro_sensors_humid",
    service_name="Humidity %s",
    discovery_function=discover_ispro_sensors_humid,
    check_function=check_ispro_sensors_humid,
    check_ruleset_name="humidity",
    check_default_parameters={},
)
