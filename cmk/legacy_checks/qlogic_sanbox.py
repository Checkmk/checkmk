#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

qlogic_sanbox_status_map = [
    "undefined",  # 0
    "unknown",  # 1
    "other",  # 2
    "ok",  # 3
    "warning",  # 4
    "failed",  # 5
]


def _status_from_sensor(sensor_status: int) -> State:
    if sensor_status == 3:
        return State.OK
    if sensor_status == 4:
        return State.WARN
    if sensor_status == 5:
        return State.CRIT
    return State.UNKNOWN


def _clean_sensor_id(sensor_id: str) -> str:
    return sensor_id.replace("16.0.0.192.221.48.", "").replace(".0.0.0.0.0.0.0.0", "")


def parse_qlogic_sanbox(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_qlogic_sanbox = SimpleSNMPSection(
    name="qlogic_sanbox",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.14"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.3.94.1.8.1",
        oids=["3", "4", "6", "7", "8", OIDEnd()],
    ),
    parse_function=parse_qlogic_sanbox,
)


#   .--temp----------------------------------------------------------------.


def discover_qlogic_sanbox_temp(section: StringTable) -> DiscoveryResult:
    for (
        sensor_name,
        _sensor_status,
        _sensor_message,
        sensor_type,
        sensor_characteristic,
        sensor_id,
    ) in section:
        if (
            sensor_type == "8"
            and sensor_characteristic == "3"
            and sensor_name != "Temperature Status"
        ):
            yield Service(item=_clean_sensor_id(sensor_id))


def check_qlogic_sanbox_temp(item: str, section: StringTable) -> CheckResult:
    for (
        _sensor_name,
        sensor_status_raw,
        sensor_message,
        _sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in section:
        if _clean_sensor_id(sensor_id) != item:
            continue

        sensor_status = int(sensor_status_raw)
        if sensor_status < 0 or sensor_status >= len(qlogic_sanbox_status_map):
            sensor_status_descr = str(sensor_status)
        else:
            sensor_status_descr = qlogic_sanbox_status_map[sensor_status]

        yield Result(
            state=_status_from_sensor(sensor_status),
            summary=f"Sensor {item} is at {sensor_message} and reports status {sensor_status_descr}",
        )
        if sensor_message.endswith(" degrees C"):
            temp = int(sensor_message.replace(" degrees C", ""))
            yield Metric("temp", float(temp))
        return

    yield Result(state=State.UNKNOWN, summary=f"No sensor {item} found")


check_plugin_qlogic_sanbox_temp = CheckPlugin(
    name="qlogic_sanbox_temp",
    service_name="Temperature Sensor %s",
    sections=["qlogic_sanbox"],
    discovery_function=discover_qlogic_sanbox_temp,
    check_function=check_qlogic_sanbox_temp,
)


#   .--power supplies------------------------------------------------------.


def discover_qlogic_sanbox_psu(section: StringTable) -> DiscoveryResult:
    for (
        _sensor_name,
        _sensor_status,
        _sensor_message,
        sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in section:
        if sensor_type == "5":
            yield Service(item=_clean_sensor_id(sensor_id))


def check_qlogic_sanbox_psu(item: str, section: StringTable) -> CheckResult:
    for (
        _sensor_name,
        sensor_status_raw,
        _sensor_message,
        _sensor_type,
        _sensor_characteristic,
        sensor_id,
    ) in section:
        if _clean_sensor_id(sensor_id) != item:
            continue

        sensor_status = int(sensor_status_raw)
        if sensor_status < 0 or sensor_status >= len(qlogic_sanbox_status_map):
            sensor_status_descr = str(sensor_status)
        else:
            sensor_status_descr = qlogic_sanbox_status_map[sensor_status]

        yield Result(
            state=_status_from_sensor(sensor_status),
            summary=f"Power Supply {item} reports status {sensor_status_descr}",
        )
        return

    yield Result(state=State.UNKNOWN, summary=f"No sensor {item} found")


check_plugin_qlogic_sanbox_psu = CheckPlugin(
    name="qlogic_sanbox_psu",
    service_name="PSU %s",
    sections=["qlogic_sanbox"],
    discovery_function=discover_qlogic_sanbox_psu,
    check_function=check_qlogic_sanbox_psu,
)
