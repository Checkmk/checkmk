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

from typing import Any, Dict, List, Mapping, NamedTuple, Optional
from .agent_based_api.v1 import (
    any_of,
    check_levels,
    register,
    OIDEnd,
    Result,
    Service,
    startswith,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from .utils.temperature import check_temperature, TempParamType

OIDSysDescr = ".1.3.6.1.2.1.1.1.0"

ENTITY_SENSOR_TYPES = {
    "1": ("other", "other"),
    "2": ("unknown", "unknown"),
    "3": ("voltage", "V"),
    "4": ("voltage", "V"),
    "5": ("current", "A"),
    "6": ("power", "W"),
    "7": ("freqeuncy", "hz"),
    "8": ("temp", "c"),
    "9": ("percent", "%"),
    "10": ("fan", "RPM"),
    "11": ("volume", "cmm"),  # cubic decimetre dm^3
    "12": ("power_presence", "boolean"),
}

ENTITY_SENSOR_SCALING = {
    "1": 10**(-24),
    "2": 10**(-21),
    "3": 10**(-18),
    "4": 10**(-15),
    "5": 10**(-12),
    "6": 10**(-9),
    "7": 10**(-6),
    "8": 10**(-3),
    "9": 1,
    "10": 10**(3),
    "11": 10**(6),
    "12": 10**(9),
    "13": 10**(12),
    "14": 10**(15),
    "15": 10**(18),
    "16": 10**(21),
    "17": 10**(24),
}


class EntitySensor(NamedTuple):
    name: str
    reading: float
    unit: str
    state: State
    status_descr: str


EntitySensorSection = Dict[str, Dict[str, EntitySensor]]


def _sensor_status_descr(status_nr: str) -> str:
    return {
        "1": "OK",
        "2": "unavailable",
        "3": "non-operational",
    }.get(status_nr, status_nr)


def _sensor_state(status_nr: str) -> State:
    return {
        "1": State.OK,
        "2": State.CRIT,
        "3": State.WARN,
    }.get(status_nr, State.UNKNOWN)


def _reformat_sensor_name(name: str) -> str:
    new_name = name
    for s in ['Fan', 'Temperature', '#', '@', 'Sensor']:
        new_name = new_name.replace(s, '')
    while '  ' in new_name:
        new_name = new_name.replace('  ', ' ')
    return f'Sensor {new_name.strip()}'


def _unit_from_device_unit(unit: str) -> Optional[str]:
    '''Converts device units to units known by Check_mk'''
    return {
        'celsius': 'c',
        'fahrenheit': 'f',
        'kelvin': 'k',
    }.get(unit)


def parse_entity_sensors(string_table: List[StringTable]) -> EntitySensorSection:
    section: EntitySensorSection = {}
    sensor_names = {i[0]: i[1] for i in string_table[0]}
    for oid_end, sensor_type_nr, scaling_nr, reading, status_nr, device_unit in string_table[1]:
        # Some devices such as Palo Alto Network series 3000 support
        # the ENTITY-MIB including sensor/entity names.
        # Others (e.g. Palo Alto Networks Series 200) do not support
        # this MIB, thus we use OID as item instead
        sensor_name = _reformat_sensor_name(sensor_names.get(oid_end, oid_end))
        sensor_type, default_unit = ENTITY_SENSOR_TYPES[sensor_type_nr]
        section.setdefault(sensor_type, {})[sensor_name] = EntitySensor(
            name=sensor_name,
            reading=float(reading) * ENTITY_SENSOR_SCALING[scaling_nr],
            unit=_unit_from_device_unit(device_unit.lower()) or default_unit,
            state=_sensor_state(status_nr),
            status_descr=_sensor_status_descr(status_nr),
        )
    return section


register.snmp_section(
    name='entity_sensors',
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
    yield from (Service(item=item) for item in section.get('temp', {}))


def check_entity_sensors_temp(
    item: str,
    params: TempParamType,
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get('temp', {}).get(item)):
        return

    yield from check_temperature(
        sensor_reading.reading,
        params,
        unique_name="temp",
        dev_unit=sensor_reading.unit,
        dev_status=int(sensor_reading.state),
        dev_status_name=sensor_reading.status_descr,
    )


register.check_plugin(
    name='entity_sensors_temp',
    sections=['entity_sensors'],
    service_name='Temperature %s',
    discovery_function=discover_entity_sensors_temp,
    check_function=check_entity_sensors_temp,
    check_ruleset_name='temperature',
    check_default_parameters={},  # The check processes ambient and CPU temp sensors,
    # which would each require totally different defaults. So it is better not to define any.
)


def discover_entity_sensors_fan(section: EntitySensorSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get('fan', {}))


def check_entity_sensors_fan(
    item: str,
    params: Mapping[str, Any],
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get('fan', {}).get(item)):
        return

    yield Result(state=sensor_reading.state,
                 summary=f"Operational status: {sensor_reading.status_descr}")

    yield from check_levels(
        value=sensor_reading.reading,
        metric_name="fan" if params.get('output_metrics') else None,
        levels_upper=params.get("upper"),
        levels_lower=params["lower"],
        render_func=lambda r: f'{int(r)} {sensor_reading.unit}',
        label="Speed",
        boundaries=(0, None),
    )


register.check_plugin(
    name='entity_sensors_fan',
    sections=['entity_sensors'],
    service_name='Fan %s',
    discovery_function=discover_entity_sensors_fan,
    check_function=check_entity_sensors_fan,
    check_ruleset_name='hw_fans',
    check_default_parameters={'lower': (2000, 1000)},  # customer request
)


def discover_entity_sensors_power_presence(section: EntitySensorSection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.get('power_presence', {}))


def check_entity_sensors_power_presence(
    item: str,
    params: Mapping[str, Any],
    section: EntitySensorSection,
) -> CheckResult:
    if not (sensor_reading := section.get('power_presence', {}).get(item)):
        return

    if sensor_reading.reading == 1:
        yield Result(state=State.OK, summary='Powered on')
        return

    yield Result(state=State(params['power_off_criticality']), summary='Powered off')


register.check_plugin(
    name='entity_sensors_power_presence',
    sections=['entity_sensors'],
    service_name='Power %s',
    discovery_function=discover_entity_sensors_power_presence,
    check_function=check_entity_sensors_power_presence,
    check_ruleset_name='power_presence',
    check_default_parameters={'power_off_criticality': 1},  # customer request
)
