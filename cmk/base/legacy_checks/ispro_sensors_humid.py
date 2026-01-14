#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.ispro import ispro_sensors_alarm_states
from cmk.plugins.ispro.lib import DETECT_ISPRO_SENSORS

check_info = {}

# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.2.1 "Humidity-R" --> ISPRO-MIB::isDeviceMonitorHumidityName
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.3.1 4407 --> ISPRO-MIB::isDeviceMonitorHumidity
# .1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1.4.1 3 --> ISPRO-MIB::isDeviceMonitorHumidityAlarm


def discover_ispro_sensors_humid(info):
    return [(name, None) for name, _reading_str, status in info if status not in ["1", "2"]]


def check_ispro_sensors_humid(item, params, info):
    for name, reading_str, status in info:
        if item == name:
            devstatus, devstatus_name = ispro_sensors_alarm_states(status)
            yield devstatus, "Device status: %s" % devstatus_name
            yield check_humidity(float(reading_str) / 100.0, params)


def parse_ispro_sensors_humid(string_table: StringTable) -> StringTable:
    return string_table


check_info["ispro_sensors_humid"] = LegacyCheckDefinition(
    name="ispro_sensors_humid",
    parse_function=parse_ispro_sensors_humid,
    detect=DETECT_ISPRO_SENSORS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19011.1.3.2.1.3.1.2.1",
        oids=["2", "3", "4"],
    ),
    service_name="Humidity %s",
    discovery_function=discover_ispro_sensors_humid,
    check_function=check_ispro_sensors_humid,
    check_ruleset_name="humidity",
)
