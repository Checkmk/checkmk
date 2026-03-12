#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from itertools import islice
from typing import NamedTuple

from cmk.agent_based.v1 import State
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


def parse_ra32e_internal_sensors(internal: StringTable) -> InternalSection | None:
    if len(internal) == 0 or len(internal[0]) == 0:
        return None

    return InternalSection(
        temperature=float(internal[0][0]) / 100.0,
        humidity=float(internal[0][1]) / 100.0,
        heat_index=float(internal[0][2]) / 100.0,
    )


def parse_ra32e_digital_sensors(sensors: StringTable) -> DigitalSection | None:
    if len(sensors) == 0:
        return None

    def type_of(sensor: list[str]) -> str | None:
        def values_until(x: int) -> bool:
            return all(sensor[:x]) and not any(sensor[x:])

        if values_until(2):
            return "temp"
        if values_until(3):
            return "temp/active"
        if values_until(4):
            return "temp/analog"
        if values_until(5):
            return "temp/humidity"
        return None

    parsed: DigitalSection | None
    sensor_data = sensors[0]
    type_ = type_of(sensor_data)

    if type_ is None:
        return None

    # uses the format of elphase.include for power and voltage
    if type_ == "temp":
        temperature, _, _, _, _ = sensor_data
        parsed = DigitalSection(
            temperature=float(temperature) / 100.0,
        )
    elif type_ == "temp/active":
        temperature, _, power_state, _, _ = sensor_data
        parsed = DigitalSection(
            temperature=float(temperature) / 100.0,
            power=power_state == "1",
        )
    elif type_ == "temp/analog":
        temperature, _, voltage, _, _ = sensor_data
        parsed = DigitalSection(
            temperature=float(temperature) / 100.0,
            voltage=int(voltage),
        )
    elif type_ == "temp/humidity":
        temperature, _, humidity, _, heat_index = sensor_data
        parsed = DigitalSection(
            temperature=float(temperature) / 100.0,
            humidity=float(humidity) / 100.0,
            heat_index=float(heat_index) / 100.0,
        )

    return parsed


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
    section_ra32e_internal_sensors: InternalSection | None,
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> CheckResult:
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    yield from _check_ra32e_temperature_sensors(
        get_value_store(), item, params, section_ra32e_internal_sensors, sections
    )


def discover_ra32e_temperature_sensors(
    section_ra32e_internal_sensors: InternalSection | None,
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> DiscoveryResult:
    if section_ra32e_internal_sensors is not None:
        yield Service(item="Internal")
        yield Service(item="Heat Index")

    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    for i, section in enumerate(sections):
        if section is None:
            continue

        if section.heat_index is not None:
            yield Service(item=index_to_heat_index(i))

        if section.temperature is not None:
            yield Service(item=index_to_sensor(i))


snmp_section_ra32e_internal_temperature = SimpleSNMPSection(
    name="ra32e_internal_sensors",
    detect=DETECT_RA32E,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.1",
        oids=["1.2", "2.1", "4.2"],
    ),
    parse_function=parse_ra32e_internal_sensors,
)

check_plugin_ra32e_sensors = CheckPlugin(
    name="ra32e_sensors",
    sections=["ra32e_internal_sensors"]
    + ["ra32e_digital_sensor_" + str(num) for num in range(1, 9)],
    service_name="Temperature %s",
    discovery_function=discover_ra32e_temperature_sensors,
    check_function=check_ra32e_temperature_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)


def _define_digital_snmp_section(number: str) -> SimpleSNMPSection[StringTable, DigitalSection]:
    return SimpleSNMPSection(
        name="ra32e_digital_sensor_" + number,
        detect=DETECT_RA32E,
        fetch=SNMPTree(
            base=".1.3.6.1.4.1.20916.1.8.1.2." + number,
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
        ),
        parse_function=parse_ra32e_digital_sensors,
    )


snmp_section_ra32e_internal_digital_1 = _define_digital_snmp_section("1")
snmp_section_ra32e_internal_digital_2 = _define_digital_snmp_section("2")
snmp_section_ra32e_internal_digital_3 = _define_digital_snmp_section("3")
snmp_section_ra32e_internal_digital_4 = _define_digital_snmp_section("4")
snmp_section_ra32e_internal_digital_5 = _define_digital_snmp_section("5")
snmp_section_ra32e_internal_digital_6 = _define_digital_snmp_section("6")
snmp_section_ra32e_internal_digital_7 = _define_digital_snmp_section("7")
snmp_section_ra32e_internal_digital_8 = _define_digital_snmp_section("8")


def check_ra32e_humidity_sensors(
    item: str,
    params: CheckParams,
    section_ra32e_internal_sensors: InternalSection | None,
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> CheckResult:
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    internal = section_ra32e_internal_sensors
    if internal is not None and item == "Internal":
        yield from check_humidity(internal.humidity, params)

    index = name_to_index(item)
    if index is None:
        return
    section = sections[index]
    if section is None or section.humidity is None:
        return

    yield from check_humidity(section.humidity, params)


def discover_ra32e_sensors_humidity(
    section_ra32e_internal_sensors: InternalSection | None,
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> DiscoveryResult:
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    if section_ra32e_internal_sensors is not None:
        yield Service(item="Internal")
    for i, section in enumerate(sections):
        if section is None or section.humidity is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_humidity = CheckPlugin(
    name="ra32e_sensors_humidity",
    service_name="Humidity %s",
    sections=["ra32e_internal_sensors"]
    + ["ra32e_digital_sensor_" + str(num) for num in range(1, 9)],
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
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> CheckResult:
    index = name_to_index(item)
    if index is None:
        return
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    section = sections[index]
    if section is None or section.voltage is None:
        return
    yield from check_elphase(
        params,
        ElPhase(
            voltage=ReadingWithState(
                value=float(section.voltage),
                state=ReadingState(state=State.OK, text="Voltage reading"),
            ),
        ),
    )


def discover_ra32e_sensors_voltage(
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> DiscoveryResult:
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    for i, section in enumerate(sections):
        if section is None or section.voltage is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_voltage = CheckPlugin(
    name="ra32e_sensors_voltage",
    service_name="Voltage %s",
    sections=["ra32e_digital_sensor_" + str(num) for num in range(1, 9)],
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
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> CheckResult:
    index = name_to_index(item)
    if index is None:
        return
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]

    for section in islice(sections, index, index + 1):
        if section is None or section.power is None:
            continue
        state = (State.OK, "power detected") if section.power else (State.CRIT, "no power detected")
        yield from check_elphase(
            params,
            ElPhase(
                device_state=state,
            ),
        )


def discover_ra32e_sensors_power(
    section_ra32e_digital_sensor_1: DigitalSection | None,
    section_ra32e_digital_sensor_2: DigitalSection | None,
    section_ra32e_digital_sensor_3: DigitalSection | None,
    section_ra32e_digital_sensor_4: DigitalSection | None,
    section_ra32e_digital_sensor_5: DigitalSection | None,
    section_ra32e_digital_sensor_6: DigitalSection | None,
    section_ra32e_digital_sensor_7: DigitalSection | None,
    section_ra32e_digital_sensor_8: DigitalSection | None,
) -> DiscoveryResult:
    sections = [
        section_ra32e_digital_sensor_1,
        section_ra32e_digital_sensor_2,
        section_ra32e_digital_sensor_3,
        section_ra32e_digital_sensor_4,
        section_ra32e_digital_sensor_5,
        section_ra32e_digital_sensor_6,
        section_ra32e_digital_sensor_7,
        section_ra32e_digital_sensor_8,
    ]
    for i, section in enumerate(sections):
        if section is None or section.power is None:
            continue
        yield Service(item=index_to_sensor(i))


check_plugin_ra32e_sensors_power = CheckPlugin(
    name="ra32e_sensors_power",
    service_name="Power State %s",
    sections=["ra32e_digital_sensor_" + str(num) for num in range(1, 9)],
    discovery_function=discover_ra32e_sensors_power,
    check_function=check_ra32e_power_sensors,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
