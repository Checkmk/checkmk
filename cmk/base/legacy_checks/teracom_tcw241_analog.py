#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree

check_info = {}


class AnalogSensor(NamedTuple):
    description: str
    maximum: float
    minimum: float
    voltage: float


_TABLES = ["1", "2", "3", "4"]


def parse_tcw241_analog(string_table):
    """
    parse string_table data and create list of namedtuples for 4 analog sensors.

    expected string_table structure:
        list of 4 analog sensors:
            [description, maximum , minimum]
            ..
            [description, maximum , minimum]
        list of analog voltages:
            [voltage1, voltage2, voltage3, voltage4]

    converted to list structure:
        [AnalogSensor(description maximum minimum voltage)]

    :param string_table: parsed snmp data
    :return: list of namedtuples for analog sensors
    """
    try:
        sensor_parameter, voltages = string_table[:4], string_table[4][0]
    except IndexError:
        return {}

    info_dict = {}
    for item, ((description, maximum, minimum),), voltage in zip(
        _TABLES, sensor_parameter, voltages
    ):
        try:
            sensor_voltage = float(voltage) / 1000.0
            sensor_maximum = float(maximum) / 1000.0
            sensor_minimum = float(minimum) / 1000.0
        except ValueError:
            continue

        if sensor_minimum < 1 or sensor_maximum < 1:
            continue

        info_dict[item] = AnalogSensor(
            description=str(description),
            maximum=sensor_maximum,
            minimum=sensor_minimum,
            voltage=sensor_voltage,
        )
    return info_dict


def check_tcw241_analog(item, params, parsed):
    """
    Check sensor data if value is in range

    :param item: sensor number
    :param params: <not used>
    :param sensor: analog sensor data
    :return: status
    """
    if not (sensor := parsed.get(item)):
        return
    yield check_levels(
        sensor.voltage,
        "voltage",
        (sensor.minimum, sensor.maximum),
        unit="V",
        infoname="[%s]" % sensor.description,
    )


def discover_teracom_tcw241_analog(section):
    yield from ((item, {}) for item in section)


check_info["teracom_tcw241_analog"] = LegacyCheckDefinition(
    name="teracom_tcw241_analog",
    detect=contains(".1.3.6.1.2.1.1.1.0", "Teracom"),
    fetch=[
        *(
            SNMPTree(
                f".1.3.6.1.4.1.38783.3.2.2.2.{table}",
                [
                    "1",  # Voltage description
                    "2",  # Voltage maximum x1000 in Integer format
                    "3",  # Voltage minimum x1000 in Integer format
                ],
            )
            for table in _TABLES
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.38783.3.3.2",
            oids=["1.0", "2.0", "3.0", "4.0"],
        ),
    ],
    parse_function=parse_tcw241_analog,
    service_name="Analog Sensor %s",
    discovery_function=discover_teracom_tcw241_analog,
    check_function=check_tcw241_analog,
)
