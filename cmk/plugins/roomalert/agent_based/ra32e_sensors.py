#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping, Sequence
from enum import StrEnum
from itertools import islice
from typing import NamedTuple

from cmk.agent_based.v1 import State
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingState, ReadingWithState
from cmk.plugins.lib.humidity import check_humidity, CheckParams
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.roomalert.lib import DETECT_RA32E


class DigitalSection(NamedTuple):
    temperature: None | float = None
    heat_index: None | float = None
    humidity: None | float = None
    voltage: None | int = None
    power: None | bool = None


class InternalSection(NamedTuple):
    temperature: float
    humidity: float
    heat_index: float


class Ra32eSection(NamedTuple):
    internal: InternalSection | None
    digital: list[DigitalSection | None]


class DigitalSensorType(StrEnum):
    TEMP = "temp"
    TEMP_ACTIVE_POWER = "temp/active_power"
    TEMP_ANALOG = "temp/analog"
    TEMP_HUMIDITY = "temp/humidity"


def _parse_ra32e_internal(table: StringTable) -> InternalSection | None:
    if len(table) == 0 or len(table[0]) == 0:
        return None

    return InternalSection(
        temperature=float(table[0][0]) / 100.0,
        humidity=float(table[0][1]) / 100.0,
        heat_index=float(table[0][2]) / 100.0,
    )


def _parse_ra32e_digital_sensor(sensors: StringTable) -> DigitalSection | None:
    if len(sensors) == 0:
        return None

    def type_of(sensor: list[str]) -> DigitalSensorType | None:
        def values_until(x: int) -> bool:
            return all(sensor[:x]) and not any(sensor[x:])

        if values_until(2):
            return DigitalSensorType.TEMP
        if values_until(3):
            return DigitalSensorType.TEMP_ACTIVE_POWER
        if values_until(4):
            return DigitalSensorType.TEMP_ANALOG
        if values_until(5):
            return DigitalSensorType.TEMP_HUMIDITY
        return None

    sensor_data = sensors[0]
    type_ = type_of(sensor_data)

    match type_:
        case DigitalSensorType.TEMP:
            temperature, _, _, _, _ = sensor_data
            return DigitalSection(
                temperature=float(temperature) / 100.0,
            )
        case DigitalSensorType.TEMP_ACTIVE_POWER:
            temperature, _, power_state, _, _ = sensor_data
            return DigitalSection(
                temperature=float(temperature) / 100.0,
                power=power_state == "1",
            )
        case DigitalSensorType.TEMP_ANALOG:
            temperature, _, voltage, _, _ = sensor_data
            return DigitalSection(
                temperature=float(temperature) / 100.0,
                voltage=int(voltage),
            )
        case DigitalSensorType.TEMP_HUMIDITY:
            temperature, _, humidity, _, heat_index = sensor_data
            return DigitalSection(
                temperature=float(temperature) / 100.0,
                humidity=float(humidity) / 100.0,
                heat_index=float(heat_index) / 100.0,
            )
        case None:
            return None


def parse_ra32e_sensors(string_table: Sequence[StringTable]) -> Ra32eSection | None:
    internal_table, *digital_tables = string_table
    internal = _parse_ra32e_internal(internal_table)
    digital = [_parse_ra32e_digital_sensor(t) for t in digital_tables]
    if internal is None and not any(digital):
        return None
    return Ra32eSection(internal=internal, digital=digital)


def is_heat_index_name(name: str) -> bool:
    return name.startswith("Heat Index")


def name_to_index(name: str) -> int | None:
    if name.startswith("Sensor ") or name.startswith("Heat Index "):
        return int(name.replace("Sensor ", "").replace("Heat Index ", "")) - 1
    return None


def index_to_sensor(index: int) -> str:
    return "Sensor " + str(index + 1)


def index_to_heat_index(index: int) -> str:
    return "Heat Index " + str(index + 1)


def _check_ra32e_temperature_sensors(
    value_store: MutableMapping[str, object],
    item: str,
    params: TempParamType,
    internal: InternalSection | None,
    sections: list[DigitalSection | None] = [],
) -> CheckResult:
    if internal is not None and item in {"Internal", "Heat Index"}:
        unique_name = "ra32e_temp_heatindex" if is_heat_index_name(item) else "ra32e_temp_internal"
        value = internal.heat_index if is_heat_index_name(item) else internal.temperature
        yield from check_temperature(
            reading=value,
            params=params,
            unique_name=unique_name,
            value_store=value_store,
        )

    index = name_to_index(item)

    if index is None:
        return

    section = sections[index]
    if section is None:
        return
    unique_name = "ra32e_temp_%s" % item.lower().replace(" ", "")
    if is_heat_index_name(item) and section.heat_index is not None:
        yield from check_temperature(
            reading=section.heat_index,
            params=params,
            unique_name=unique_name,
            value_store=value_store,
        )
    elif section.temperature is not None:
        yield from check_temperature(
            reading=section.temperature,
            params=params,
            unique_name=unique_name,
            value_store=value_store,
        )


def check_ra32e_temperature_sensors(
    item: str,
    params: TempParamType,
    section: Ra32eSection | None,
) -> CheckResult:
    if section is None:
        return
    yield from _check_ra32e_temperature_sensors(
        get_value_store(),
        item,
        params,
        section.internal,
        section.digital,
    )


def discover_ra32e_temperature_sensors(
    section: Ra32eSection | None,
) -> DiscoveryResult:
    if section is None:
        return

    if section.internal is not None:
        yield Service(item="Internal")
        yield Service(item="Heat Index")

    for i, digital_section in enumerate(section.digital):
        if digital_section is None:
            continue

        if digital_section.heat_index is not None:
            yield Service(item=index_to_heat_index(i))

        if digital_section.temperature is not None:
            yield Service(item=index_to_sensor(i))


snmp_section_ra32e_sensors = SNMPSection(
    name="ra32e_sensors",
    detect=DETECT_RA32E,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.20916.1.8.1.1",
            oids=["1.2", "2.1", "4.2"],
        ),
        *(
            SNMPTree(
                base=f".1.3.6.1.4.1.20916.1.8.1.2.{i}",
                oids=[
                    # Note:
                    # The output depends on the kind of sensor and a sensor only outputs relevant values.
                    # The following sensors are mentioned in the MIB from the 13th September 2017:
                    #
                    # sensor            | values
                    # ---------------------------------
                    # Temperature       | 1, 2
                    # Temp/Active Power | 1, 2, 3
                    # Temp/Analog       | 1, 2, 3, 4
                    # Temp/Humidity     | 1, 2, 3, 4, 5
                    #
                    "1",  # digital-sen[1-8]-1 --> Temperature in Celsius for any of: Temperature | Temp/Humidity | Temp/Analog | Temp/Active Power.
                    "2",  # digital-sen[1-8]-2 --> Temperature in Fahrenheit for any of: Temperature | Temp/Humidity | Temp/Analog | Temp/Active Power.
                    "3",  # digital-sen[1-8]-3 --> Humidity percentage IF Temp/Humidity. Voltage IF Temp/Analog. Power state boolean IF Temp/Active Power.
                    "4",  # digital-sen[1-8]-4 --> Heat index Fahrenheit IF Temp/Humidity. Current IF Temp/Analog.
                    "5",  # digital-sen[1-8]-5 --> Heat index Celsius IF Temp/Humidity.
                ],
            )
            for i in range(1, 9)
        ),
    ],
    parse_function=parse_ra32e_sensors,
)

check_plugin_ra32e_sensors = CheckPlugin(
    name="ra32e_sensors",
    sections=["ra32e_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_ra32e_temperature_sensors,
    check_function=check_ra32e_temperature_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)


def check_ra32e_humidity_sensors(
    item: str,
    params: CheckParams,
    section: Ra32eSection | None,
) -> CheckResult:
    if section is None:
        return

    internal = section.internal
    if internal is not None and item == "Internal":
        yield from check_humidity(internal.humidity, params)

    index = name_to_index(item)
    if index is None:
        return
    digital_section = section.digital[index]
    if digital_section is None or digital_section.humidity is None:
        return

    yield from check_humidity(digital_section.humidity, params)


def discover_ra32e_sensors_humidity(
    section: Ra32eSection | None,
) -> DiscoveryResult:
    if section is None:
        return

    if section.internal is not None:
        yield Service(item="Internal")

    for i, digital_section in enumerate(section.digital):
        if digital_section is None or digital_section.humidity is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_humidity = CheckPlugin(
    name="ra32e_sensors_humidity",
    service_name="Humidity %s",
    sections=["ra32e_sensors"],
    discovery_function=discover_ra32e_sensors_humidity,
    check_function=check_ra32e_humidity_sensors,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)


def check_ra32e_sensors_voltage(
    item: str,
    params: Mapping[str, object],
    section: Ra32eSection | None,
) -> CheckResult:
    if section is None:
        return

    index = name_to_index(item)
    if index is None:
        return
    digital_section = section.digital[index]
    if digital_section is None or digital_section.voltage is None:
        return
    yield from check_elphase(
        params,
        ElPhase(
            voltage=ReadingWithState(
                value=float(digital_section.voltage),
                state=ReadingState(state=State.OK, text="Voltage reading"),
            ),
        ),
    )


def discover_ra32e_sensors_voltage(
    section: Ra32eSection | None,
) -> DiscoveryResult:
    if section is None:
        return

    for i, digital_section in enumerate(section.digital):
        if digital_section is None or digital_section.voltage is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_voltage = CheckPlugin(
    name="ra32e_sensors_voltage",
    service_name="Voltage %s",
    sections=["ra32e_sensors"],
    discovery_function=discover_ra32e_sensors_voltage,
    check_function=check_ra32e_sensors_voltage,
    check_ruleset_name="ups_outphase",
    check_default_parameters={
        "voltage": (210, 180),
    },
)


def check_ra32e_power_sensors(
    item: str,
    params: Mapping[str, object],
    section: Ra32eSection | None,
) -> CheckResult:
    if section is None:
        return

    index = name_to_index(item)
    if index is None:
        return

    for digital_section in islice(section.digital, index, index + 1):
        if digital_section is None or digital_section.power is None:
            continue
        state = (
            (State.OK, "power detected")
            if digital_section.power
            else (State.CRIT, "no power detected")
        )
        yield from check_elphase(
            params,
            ElPhase(
                device_state=state,
            ),
        )


def discover_ra32e_sensors_power(
    section: Ra32eSection | None,
) -> DiscoveryResult:
    if section is None:
        return

    for i, digital_section in enumerate(section.digital):
        if digital_section is None or digital_section.power is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_power = CheckPlugin(
    name="ra32e_sensors_power",
    service_name="Power State %s",
    sections=["ra32e_sensors"],
    discovery_function=discover_ra32e_sensors_power,
    check_function=check_ra32e_power_sensors,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
