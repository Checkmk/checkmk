#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.47.1.1.1.1.7.1 PA-500
# .1.3.6.1.2.1.47.1.1.1.1.7.2 Fan #1 Operational
# .1.3.6.1.2.1.47.1.1.1.1.7.3 Fan #2 Operational
# .1.3.6.1.2.1.47.1.1.1.1.7.4 Temperature at MP [U6]
# .1.3.6.1.2.1.47.1.1.1.1.7.5 Temperature at DP [U7]

# .1.3.6.1.2.1.99.1.1.1.1.2 10
# .1.3.6.1.2.1.99.1.1.1.1.3 10
# .1.3.6.1.2.1.99.1.1.1.1.4 8
# .1.3.6.1.2.1.99.1.1.1.1.5 8
# .1.3.6.1.2.1.99.1.1.1.2.2 9
# .1.3.6.1.2.1.99.1.1.1.2.3 9
# .1.3.6.1.2.1.99.1.1.1.2.4 9
# .1.3.6.1.2.1.99.1.1.1.2.5 9
# .1.3.6.1.2.1.99.1.1.1.4.2 1
# .1.3.6.1.2.1.99.1.1.1.4.3 1
# .1.3.6.1.2.1.99.1.1.1.4.4 37
# .1.3.6.1.2.1.99.1.1.1.4.5 40
# .1.3.6.1.2.1.99.1.1.1.5.2 1
# .1.3.6.1.2.1.99.1.1.1.5.3 1
# .1.3.6.1.2.1.99.1.1.1.5.4 1
# .1.3.6.1.2.1.99.1.1.1.5.5 1

from typing import Any, List, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    any_of,
    check_levels,
    get_value_store,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import entity_sensors as utils
from cmk.base.plugins.agent_based.utils.entity_sensors import EntitySensorSection, OIDSysDescr
from cmk.base.plugins.agent_based.utils.temperature import check_temperature, TempParamType


def parse_entity_sensors(string_table: List[StringTable]) -> EntitySensorSection:
    return utils.parse_entity_sensors(string_table)


register.snmp_section(
    name="entity_sensors",
    detect=any_of(
        startswith(OIDSysDescr, "palo alto networks"),
        startswith(OIDSysDescr, "cisco adaptive security appliance"),
    ),
    parse_function=parse_entity_sensors,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[
                OIDEnd(),
                "7",  # ENTITY-MIB::entPhysicalName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.99.1.1.1",
            oids=[
                OIDEnd(),
                "1",  # entPhySensorType
                "2",  # entPhySensorScale
                "4",  # entPhySensorValue
                "5",  # entPhySensorOperStatus
                "6",  # entPhySensorUnitsDisplay
            ],
        ),
    ],
)


def discover_entity_sensors_temp(section: EntitySensorSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get("temp", {}))


def check_entity_sensors_temp(
    item: str,
    params: TempParamType,
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get("temp", {}).get(item)):
        return

    yield from check_temperature(
        sensor_reading.reading,
        params,
        unique_name="temp",
        value_store=get_value_store(),
        dev_unit=sensor_reading.unit,
        dev_status=int(sensor_reading.state),
        dev_status_name=sensor_reading.status_descr,
    )


register.check_plugin(
    name="entity_sensors_temp",
    sections=["entity_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_entity_sensors_temp,
    check_function=check_entity_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},  # The check processes ambient and CPU temp sensors,
    # which would each require totally different defaults. So it is better not to define any.
)


def discover_entity_sensors_fan(section: EntitySensorSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get("fan", {}))


def check_entity_sensors_fan(
    item: str,
    params: Mapping[str, Any],
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get("fan", {}).get(item)):
        return

    yield Result(
        state=sensor_reading.state, summary=f"Operational status: {sensor_reading.status_descr}"
    )

    yield from check_levels(
        value=sensor_reading.reading,
        metric_name="fan" if params.get("output_metrics") else None,
        levels_upper=params.get("upper"),
        levels_lower=params["lower"],
        render_func=lambda r: f"{int(r)} {sensor_reading.unit}",
        label="Speed",
        boundaries=(0, None),
    )


register.check_plugin(
    name="entity_sensors_fan",
    sections=["entity_sensors"],
    service_name="Fan %s",
    discovery_function=discover_entity_sensors_fan,
    check_function=check_entity_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (2000, 1000)},  # customer request
)


def discover_entity_sensors_power_presence(section: EntitySensorSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get("power_presence", {}))


def check_entity_sensors_power_presence(
    item: str,
    params: Mapping[str, Any],
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get("power_presence", {}).get(item)):
        return

    if sensor_reading.reading == 1:
        yield Result(state=State.OK, summary="Powered on")
        return

    yield Result(state=State(params["power_off_criticality"]), summary="Powered off")


register.check_plugin(
    name="entity_sensors_power_presence",
    sections=["entity_sensors"],
    service_name="Power %s",
    discovery_function=discover_entity_sensors_power_presence,
    check_function=check_entity_sensors_power_presence,
    check_ruleset_name="power_presence",
    check_default_parameters={"power_off_criticality": 1},  # customer request
)
