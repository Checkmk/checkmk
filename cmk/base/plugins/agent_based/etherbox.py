#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs

# The etherbox supports the following sensor types on each port
# sensor types
# 0 = no sensor
# 1 = temperature      - implemented
# 2 = brightness
# 3 = humidity         - implemented
# 4 = switch contact   - implemented
# 5 = voltage detector
# 6 = smoke sensor     - implemented

# Note: The short contact config option in the etherbox is of type switch contact
#       The short contact status is set for 15 seconds after a button press

from dataclasses import dataclass
from typing import Any, List, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    Metric,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import humidity, temperature


@dataclass(frozen=True)
class SensorData:
    name: str
    value: int


Index = str
Type = str


@dataclass(frozen=True)
class Section:
    unit_of_measurement: str
    sensor_data: Mapping[Index, Mapping[Type, SensorData]]


def etherbox_convert(string_table: List[StringTable]) -> Section | None:
    if not string_table[0] and not string_table[1]:
        return None
    unit_of_measurement = {"0": "c", "1": "f", "2": "k"}[string_table[0][0][0]]
    data: dict[Index, dict[Type, SensorData]] = {}
    for i in range(0, len(string_table[1])):
        index, sensor_type = string_table[1][i][1], string_table[1][i][3]
        if index not in data:
            data[index] = {}
        data[index][sensor_type] = SensorData(string_table[1][i][2], int(string_table[1][i][4]))
    return Section(unit_of_measurement, data)


# 2015:
# Older firmware version of Etherbox do not answer on
# .1.3.6.1.2.1. (sysDescr). Yurks. We need to fetch
# a vendor specific OID here and wait until all old devices
# have vanished.
# 2021:
# Have they yet? How do we know? Anyway: better would be the following,
# but we need to known what's in the sysDescr in the good case.
# return (
#    "etherbox" in oid(".1.3.6.1.2.1.1.1.0").lower() or  # TODO: "etherbox" is a wild guess
#    (not oid(".1.3.6.1.2.1.1.1.0") and
#     oid(".1.3.6.1.4.1.14848.2.1.1.1.0", "").startswith("Version"))
# )
register.snmp_section(
    name="etherbox",
    parse_function=etherbox_convert,
    detect=startswith(".1.3.6.1.4.1.14848.2.1.1.1.0", "Version"),
    fetch=[
        SNMPTree(base=".1.3.6.1.4.1.14848.2.1.1", oids=["3"]),  # temperature unit
        SNMPTree(
            base=".1.3.6.1.4.1.14848.2.1.2.1",
            oids=[
                OIDEnd(),
                "1",  # index
                "2",  # name
                "3",  # type
                "5",  # value * 10
            ],
        ),
    ],
)


def discovery(section: Section, req_sensor_type: str) -> DiscoveryResult:
    for index, index_data in section.sensor_data.items():
        for sensor_type, data in index_data.items():
            if sensor_type in ("1", "3") and data.value == 0:
                continue
            if sensor_type == req_sensor_type:
                yield Service(item=f"{index}.{sensor_type}")


class SensorException(Exception):
    pass


def etherbox_get_sensor(item: str, section: Section) -> SensorData:
    item_index, item_type = item.split(".")
    if item_index not in section.sensor_data:
        raise SensorException("Sensor not found")
    if item_type not in section.sensor_data[item_index]:
        raise SensorException(f"Sensor type changed {item}")
    return section.sensor_data[item_index][item_type]


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def check_etherbox_temp(
    item: str, params: temperature.TempParamType, section: Section
) -> CheckResult:
    try:
        data = etherbox_get_sensor(item, section)
    except SensorException as error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    temp = data.value / 10.0
    metric, result, *other = list(
        temperature.check_temperature(
            temp,
            params,
            unique_name="etherbox_temp_%s" % item,
            value_store=get_value_store(),
            dev_unit=section.unit_of_measurement,
        )
    )
    if isinstance(result, Result):
        yield Result(state=State(result.state), summary=f"[{data.name}] {result.summary}")
    yield metric
    for el in other:
        yield el


def discovery_temp(section: Section) -> DiscoveryResult:
    yield from discovery(section, "1")


register.check_plugin(
    name="etherbox_temp",
    sections=["etherbox"],
    check_function=check_etherbox_temp,
    discovery_function=discovery_temp,
    check_ruleset_name="temperature",
    service_name="Temperature %s",
    check_default_parameters={},
)
# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def check_etherbox_humidity(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    try:
        data = etherbox_get_sensor(item, section)
    except SensorException as error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    result, metrics = list(humidity.check_humidity(data.value / 10.0, params))
    if isinstance(result, Result):
        yield Result(state=State(result.state), summary=f"[{data.name}] {result.summary}")
    yield metrics


def discovery_humidity(section: Section) -> DiscoveryResult:
    yield from discovery(section, "3")


register.check_plugin(
    name="etherbox_humidity",
    sections=["etherbox"],
    check_function=check_etherbox_humidity,
    discovery_function=discovery_humidity,
    check_ruleset_name="humidity",
    service_name="Sensor %s",
    check_default_parameters={},
)
# .
#   .--switch contact------------------------------------------------------.
#   |               _ _       _                       _             _      |
#   |  _____      _(_) |_ ___| |__     ___ ___  _ __ | |_ __ _  ___| |_    |
#   | / __\ \ /\ / / | __/ __| '_ \   / __/ _ \| '_ \| __/ _` |/ __| __|   |
#   | \__ \\ V  V /| | || (__| | | | | (_| (_) | | | | || (_| | (__| |_    |
#   | |___/ \_/\_/ |_|\__\___|_| |_|  \___\___/|_| |_|\__\__,_|\___|\__|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_etherbox_switch_contact(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    try:
        data = etherbox_get_sensor(item, section)
    except SensorException as error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    state = State.OK
    switch_state = "open" if data.value == 1000 else "closed"

    extra_info = ""
    if (param_state := params["state"]) != "ignore" and switch_state != param_state:
        state = State.CRIT
        extra_info = f", should be {params}"

    infotext = f"Switch contact {switch_state}{extra_info}"
    yield Result(state=state, summary=f"[{data.name}] {infotext}")
    yield Metric("switch_contact", data.value)


def discovery_switch(section: Section) -> DiscoveryResult:
    yield from discovery(section, "4")


register.check_plugin(
    name="etherbox_switch",
    sections=["etherbox"],
    check_function=check_etherbox_switch_contact,
    discovery_function=discovery_switch,
    check_ruleset_name="switch_contact",
    service_name="Sensor %s",
    check_default_parameters={"state": "ignore"},
)
# .
#   .--smoke---------------------------------------------------------------.
#   |                                        _                             |
#   |                    ___ _ __ ___   ___ | | _____                      |
#   |                   / __| '_ ` _ \ / _ \| |/ / _ \                     |
#   |                   \__ \ | | | | | (_) |   <  __/                     |
#   |                   |___/_| |_| |_|\___/|_|\_\___|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_etherbox_smoke(item: str, section: Section) -> CheckResult:
    try:
        data = etherbox_get_sensor(item, section)
    except SensorException as error:
        yield Result(state=State.UNKNOWN, summary=str(error))
        return

    state = State.OK
    infotext = "Status: OK"
    if data.value != 0:
        infotext = "Status: smoke alarm"
        state = State.CRIT
    yield Result(state=state, summary=f"[{data.name}] {infotext}")
    yield Metric(name="smoke", value=data.value)


def discovery_smoke(section: Section) -> DiscoveryResult:
    yield from discovery(section, "6")


register.check_plugin(
    name="etherbox_smoke",
    sections=["etherbox"],
    check_function=check_etherbox_smoke,
    discovery_function=discovery_smoke,
    service_name="Sensor %s",
)
