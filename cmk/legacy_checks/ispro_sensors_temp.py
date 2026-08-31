#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS, sensors_alarm_states
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.2.1 "Temperature-R" --> ISPRO-MIB::isDeviceMonitorTemperatureName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.3.1 2230 --> ISPRO-MIB::isDeviceMonitorTemperature
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.4.1 3 --> ISPRO-MIB::isDeviceMonitorTemperatureAlarm
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.3.1 2300 --> ISPRO-MIB::isDeviceConfigTemperatureLowWarning
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.4.1 2000 --> ISPRO-MIB::isDeviceConfigTemperatureLowCritical
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.5.1 3000 --> ISPRO-MIB::isDeviceConfigTemperatureHighWarning
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.6.1 3800 --> ISPRO-MIB::isDeviceConfigTemperatureHighCritical


def discover_ispro_sensors_temp(section: StringTable) -> DiscoveryResult:
    yield from (Service(item=line[0]) for line in section if line[2] not in ["1", "2"])


def check_ispro_sensors_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for name, reading_str, status, warn_low, crit_low, warn, crit in section:
        if item == name:
            devstatus, devstatus_name = sensors_alarm_states(status)
            yield from check_temperature(
                float(reading_str) / 100.0,
                params,
                unique_name=f"ispro_sensors_temp_{item}",
                value_store=get_value_store(),
                dev_levels=(float(warn) / 100.0, float(crit) / 100.0),
                dev_levels_lower=(float(warn_low) / 100.0, float(crit_low) / 100.0),
                dev_status=int(devstatus),
                dev_status_name=devstatus_name,
            )
            return


def parse_ispro_sensors_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ispro_sensors_temp = SimpleSNMPSection(
    name="ispro_sensors_temp",
    parse_function=parse_ispro_sensors_temp,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3",
        oids=["1.1.1.2", "1.1.1.3", "1.1.1.4", "2.2.1.3", "2.2.1.4", "2.2.1.5", "2.2.1.6"],
    ),
)


check_plugin_ispro_sensors_temp = CheckPlugin(
    name="ispro_sensors_temp",
    service_name="Temperature %s",
    discovery_function=discover_ispro_sensors_temp,
    check_function=check_ispro_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
