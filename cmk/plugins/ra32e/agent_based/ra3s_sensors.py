#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from enum import StrEnum
from typing import NamedTuple

from cmk.agent_based.v1 import get_value_store, State
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState
from cmk.plugins.lib.humidity import check_humidity, CheckParams
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.ra32e.lib import DETECT_RA3S


class InternalSection(NamedTuple):
    temp_celsius: float


def parse_ra3s_internal_section_temperature(string_table: StringTable) -> InternalSection | None:
    if len(string_table) == 0 or len(string_table[0]) == 0:
        return None

    value = string_table[0][0]
    return InternalSection(temp_celsius=float(value) / 100.0)


snmp_section_ra3s_internal_sensors = SimpleSNMPSection(
    name="ra3s_internal_sensors",
    detect=DETECT_RA3S,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.13.1.1",
        oids=["1.2"],  # internal-tempc
    ),
    parse_function=parse_ra3s_internal_section_temperature,
)


class DigitalSensorType(StrEnum):
    TEMP = "temp"
    TEMP_ACTIVE_POWER = "temp/active_power"
    TEMP_ANALOG = "temp/analog"
    TEMP_HUMIDITY = "temp/humidity"
    TEMP_EXTREME = "temp/extreme"


def detect_sensor_type(raw_data: list[str]) -> DigitalSensorType | None:
    count = 0

    for value in raw_data:
        if value.isdigit():
            count += 1

    lookup = {
        2: DigitalSensorType.TEMP,
        3: DigitalSensorType.TEMP_ACTIVE_POWER,
        4: DigitalSensorType.TEMP_ANALOG,
        5: DigitalSensorType.TEMP_EXTREME,
        6: DigitalSensorType.TEMP_HUMIDITY,
    }
    return lookup.get(count)


class DigitalSection(NamedTuple):
    sensor_type: DigitalSensorType
    temperature: float
    humidity: float | None = None
    heat_index: float | None = None
    power_detected: bool | None = None
    voltage: int | None = None
    thermocouple_temperature: float | None = None


def parse_ra3s_digital(string_table: StringTable) -> DigitalSection | None:
    if len(string_table) == 0:
        return None

    sensor_data = string_table[0]
    sensor_type = detect_sensor_type(sensor_data)

    if sensor_type is None:
        return None

    temperature = float(sensor_data[0]) / 100.0
    if sensor_type == DigitalSensorType.TEMP:
        return DigitalSection(sensor_type=sensor_type, temperature=temperature)
    elif sensor_type == DigitalSensorType.TEMP_ACTIVE_POWER:
        return DigitalSection(
            sensor_type=sensor_type, temperature=temperature, power_detected=sensor_data[2] == "1"
        )
    elif sensor_type == DigitalSensorType.TEMP_ANALOG:
        return DigitalSection(
            sensor_type=sensor_type, temperature=temperature, voltage=int(sensor_data[2])
        )
    elif sensor_type == DigitalSensorType.TEMP_EXTREME:
        return DigitalSection(
            sensor_type=sensor_type,
            temperature=temperature,
            thermocouple_temperature=float(sensor_data[2]) / 100.0,
        )
    elif sensor_type == DigitalSensorType.TEMP_HUMIDITY:
        _, _, humidity, _, heat_index, _ = sensor_data
        return DigitalSection(
            sensor_type=sensor_type,
            temperature=temperature,
            humidity=float(humidity) / 100.0,
            heat_index=float(heat_index) / 100.0,
        )


snmp_section_ra3s_digital_sensors = SimpleSNMPSection(
    name="ra3s_digital_sensors",
    detect=DETECT_RA3S,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.13.1.2.1",
        oids=[
            # Note:
            # The output depends on the kind of sensor and a sensor only outputs relevant values.
            # The following sensors are mentioned in the MIB:
            #
            # sensor                      | values
            # ---------------------------------
            # Temperature                 | 1, 2
            # Temp/Active Power           | 1, 2, 3
            # Temp/Analog                 | 1, 2, 3, 4
            # Digital Extreme Temperature | 1, 2, 3, 4, 5
            # Temp/Humidity               | 1, 2, 3, 4, 5, 6
            "1",  # digital-sen1-1 --> Temperature in Celsius for any of: Temperature | Temp/Humidity | Temp/Analog | Temp/Active Power | Digital Extreme Temp.
            "2",  # digital-sen1-2 --> Temperature in Fahrenheit for any of: Temperature | Temp/Humidity | Temp/Analog | Temp/Active Power | Digital Extreme Temp.
            "3",  # digital-sen1-3 --> Humidity percentage IF Temp/Humidity. Voltage IF Temp/Analog. Power state boolean IF Temp/Active Power. Thermocouple temp in Celsius IF Digital Extreme Temp.
            "4",  # digital-sen1-4 --> Heat index Fahrenheit IF Temp/Humidity. Current IF Temp/Analog. Thermocouple temp in Fahrenheit IF Digital Extreme Temp.
            "5",  # digital-sen1-5 --> Heat index Celsius IF Temp/Humidity. Fault code IF Digital Extreme Temp.
            "6",  # digital-sen1-6 --> Dew point in Celsius IF Temp/Humidity.
        ],
    ),
    parse_function=parse_ra3s_digital,
)


def discovery_ra3s_temperature(
    section_ra3s_internal_sensors: InternalSection | None,
    section_ra3s_digital_sensors: DigitalSection | None,
) -> DiscoveryResult:
    if section_ra3s_internal_sensors is not None:
        yield Service(item="Internal")

    if section_ra3s_digital_sensors is not None:
        yield Service(item="Sensor")


def _check_ra3s_temperature(
    value_store: MutableMapping[str, object],
    item: str,
    params: TempParamType,
    internal: InternalSection | None,
    digital: DigitalSection | None,
) -> CheckResult:
    if internal is not None and item == "Internal":
        yield from check_temperature(
            reading=internal.temp_celsius,
            params=params,
            unique_name="ra3s_temp_internal",
            value_store=value_store,
        )

    if digital is not None and item == "Sensor":
        yield from check_temperature(
            reading=digital.temperature,
            params=params,
            unique_name="ra3s_temp_digital",
            value_store=value_store,
        )


def check_ra3s_temperature(
    item: str,
    params: TempParamType,
    section_ra3s_internal_sensors: InternalSection | None,
    section_ra3s_digital_sensors: DigitalSection | None,
) -> CheckResult:
    yield from _check_ra3s_temperature(
        get_value_store(), item, params, section_ra3s_internal_sensors, section_ra3s_digital_sensors
    )


check_plugin_ra3s_temperature = CheckPlugin(
    name="ra3s_internal_temperature",
    sections=["ra3s_internal_sensors", "ra3s_digital_sensors"],
    service_name="Temperature %s",
    discovery_function=discovery_ra3s_temperature,
    check_function=check_ra3s_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)


def discovery_ra3s_humidity(section: DigitalSection) -> DiscoveryResult:
    if section.sensor_type == DigitalSensorType.TEMP_HUMIDITY:
        yield Service(item="Sensor")


def check_ra3s_humidity(
    item: str,
    params: CheckParams,
    section: DigitalSection,
) -> CheckResult:
    if section.humidity is not None:
        yield from check_humidity(section.humidity, params)


check_plugin_ra3s_humidity = CheckPlugin(
    name="ra3s_sensors_humidity",
    sections=["ra3s_digital_sensors"],
    service_name="Humidity %s",
    discovery_function=discovery_ra3s_humidity,
    check_function=check_ra3s_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)


def discovery_ra3s_voltage(section: DigitalSection) -> DiscoveryResult:
    if section.sensor_type == DigitalSensorType.TEMP_ANALOG:
        yield Service(item="Sensor")


def check_ra3s_voltage(
    item: str,
    params: Mapping[str, object],
    section: DigitalSection,
) -> CheckResult:
    if section.voltage is not None:
        yield from check_elphase(
            params,
            ElPhase(
                voltage=ReadingWithState(
                    value=float(section.voltage),
                    state=ReadingState(state=State.OK, text="Voltage reading"),
                ),
            ),
        )


check_plugin_ra3s_voltage = CheckPlugin(
    name="ra3s_sensors_voltage",
    sections=["ra3s_digital_sensors"],
    service_name="Voltage %s",
    discovery_function=discovery_ra3s_voltage,
    check_function=check_ra3s_voltage,
    check_ruleset_name="ups_outphase",
    check_default_parameters={
        "voltage": (4, 6),
    },
)


def discovery_ra3s_power(section: DigitalSection) -> DiscoveryResult:
    if section.sensor_type == DigitalSensorType.TEMP_ACTIVE_POWER:
        yield Service(item="Sensor")


def check_ra3s_power(
    item: str,
    params: Mapping[str, object],
    section: DigitalSection,
) -> CheckResult:
    state = (
        (State.OK, "power detected")
        if section.power_detected
        else (State.CRIT, "no power detected")
    )
    yield from check_elphase(
        params,
        ElPhase(
            device_state=state,
        ),
    )


check_plugin_ra3s_power = CheckPlugin(
    name="ra3s_sensors_power",
    sections=["ra3s_digital_sensors"],
    service_name="Power State %s",
    discovery_function=discovery_ra3s_power,
    check_function=check_ra3s_power,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
