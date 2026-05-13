#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.didactum.lib import (
    check_didactum_sensors_humidity,
    check_didactum_sensors_temp,
    check_didactum_sensors_voltage,
    DETECT_DIDACTUM,
    discover_didactum_sensors,
    parse_didactum_sensors,
    Section,
)
from cmk.plugins.lib.temperature import TempParamType

# .1.3.6.1.4.1.46501.6.2.1.5.201007 alpha-bravo_doppelboden_frischluft --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogName.201007
# .1.3.6.1.4.1.46501.6.2.1.6.201007 normal --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogState.201007
# .1.3.6.1.4.1.46501.6.2.1.7.201007 14.9 --> DIDACTUM-SYSTEM-MIB::ctlCANSensorsAnalogValue.201007


snmp_section_didactum_can_sensors_analog = SimpleSNMPSection(
    name="didactum_can_sensors_analog",
    detect=DETECT_DIDACTUM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.46501.6.2.1",
        oids=["4", "5", "6", "7", "10", "11", "12", "13"],
    ),
    parse_function=parse_didactum_sensors,
)


def discover_didactum_can_sensors_analog_temp(section: Section) -> DiscoveryResult:
    yield from discover_didactum_sensors(section, "temperature")


def check_didactum_can_sensors_analog_temp(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from check_didactum_sensors_temp(
        item, params, section, unique_name=f"didactum_can_sensors_analog_temp.{item}"
    )


check_plugin_didactum_can_sensors_analog = CheckPlugin(
    name="didactum_can_sensors_analog",
    service_name="Temperature CAN %s",
    discovery_function=discover_didactum_can_sensors_analog_temp,
    check_function=check_didactum_can_sensors_analog_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_didactum_can_sensors_analog_humidity(section: Section) -> DiscoveryResult:
    yield from discover_didactum_sensors(section, "humidity")


def check_didactum_can_sensors_analog_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_didactum_sensors_humidity(item, params, section)


check_plugin_didactum_can_sensors_analog_humidity = CheckPlugin(
    name="didactum_can_sensors_analog_humidity",
    service_name="Humidity CAN %s",
    sections=["didactum_can_sensors_analog"],
    discovery_function=discover_didactum_can_sensors_analog_humidity,
    check_function=check_didactum_can_sensors_analog_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={},
)


def discover_didactum_can_sensors_analog_voltage(section: Section) -> DiscoveryResult:
    yield from discover_didactum_sensors(section, "voltage")


def check_didactum_can_sensors_analog_voltage(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_didactum_sensors_voltage(item, params, section)


check_plugin_didactum_can_sensors_analog_voltage = CheckPlugin(
    name="didactum_can_sensors_analog_voltage",
    service_name="Phase CAN %s",
    sections=["didactum_can_sensors_analog"],
    discovery_function=discover_didactum_can_sensors_analog_voltage,
    check_function=check_didactum_can_sensors_analog_voltage,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
