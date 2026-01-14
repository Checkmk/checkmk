#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.ispro import ispro_sensors_alarm_states
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS

check_info = {}

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.2.1 "Temperature-R" --> ISPRO-MIB::isDeviceMonitorTemperatureName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.3.1 2230 --> ISPRO-MIB::isDeviceMonitorTemperature
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.1.1.4.1 3 --> ISPRO-MIB::isDeviceMonitorTemperatureAlarm
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.3.1 2300 --> ISPRO-MIB::isDeviceConfigTemperatureLowWarning
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.4.1 2000 --> ISPRO-MIB::isDeviceConfigTemperatureLowCritical
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.5.1 3000 --> ISPRO-MIB::isDeviceConfigTemperatureHighWarning
# .1.3.6.1.4.1.19011.1.3.2.1.3.2.2.1.6.1 3800 --> ISPRO-MIB::isDeviceConfigTemperatureHighCritical


def discover_ispro_sensors_temp(info):
    return [(line[0], {}) for line in info if line[2] not in ["1", "2"]]


def check_ispro_sensors_temp(item, params, info):
    for name, reading_str, status, warn_low, crit_low, warn, crit in info:
        if item == name:
            devstatus, devstatus_name = ispro_sensors_alarm_states(status)
            return check_temperature(
                float(reading_str) / 100.0,
                params,
                "ispro_sensors_temp_%s" % item,
                dev_levels=(float(warn) / 100.0, float(crit) / 100.0),
                dev_levels_lower=(float(warn_low) / 100.0, float(crit_low) / 100.0),
                dev_status=devstatus,
                dev_status_name=devstatus_name,
            )
    return None


def parse_ispro_sensors_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["ispro_sensors_temp"] = LegacyCheckDefinition(
    name="ispro_sensors_temp",
    parse_function=parse_ispro_sensors_temp,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3",
        oids=["1.1.1.2", "1.1.1.3", "1.1.1.4", "2.2.1.3", "2.2.1.4", "2.2.1.5", "2.2.1.6"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_ispro_sensors_temp,
    check_function=check_ispro_sensors_temp,
    check_ruleset_name="temperature",
)
