#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Any, Dict, List, Mapping, NamedTuple

from .agent_based_api.v1 import (
    check_levels,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.printer import DETECT_PRINTER

printer_io_units = {
    "-1": "unknown",
    "0": "unknown",
    "1": "unknown",
    "2": "unknown",  # defined by PrtCapacityUnitTC used in newer revs.
    "3": "1/10000 in",
    "4": "micrometers",
    "8": "sheets",
    "16": "feet",
    "17": "meters",
    "18": "items",
    "19": "percent",
}


class AvailabilityStatus(enum.Enum):
    # Availability
    AVAILABLE_AND_IDLE = 0
    AVAILABLE_AND_STANDBY = 2
    AVAILABLE_AND_ACTIVE = 4
    AVAILABLE_AND_BUSY = 6
    UNAVAILABLE_AND_ON_REQUEST = 1
    UNAVAILABLE_BECAUSE_BROKEN = 3
    UNKNOWN = 5


class AlertStatus(enum.Enum):
    NONE = "None"
    NON_CRITICAL = "Non-Critical"
    CRITICAL = "Critical"


class IOType(enum.Enum):
    INPUT = "Input"
    OUTPUT = "Output"


class PrinterStates(NamedTuple):
    availability: AvailabilityStatus
    alerts: AlertStatus
    offline: bool
    transitioning: bool


class Tray(NamedTuple):
    tray_index: str
    name: str
    description: str
    states: PrinterStates
    capacity_unit: str
    capacity_max: int
    level: int


Section = Dict[str, Tray]

STATES_MAP = {
    AvailabilityStatus.AVAILABLE_AND_IDLE: State.OK,
    AvailabilityStatus.AVAILABLE_AND_STANDBY: State.OK,
    AvailabilityStatus.AVAILABLE_AND_ACTIVE: State.OK,
    AvailabilityStatus.AVAILABLE_AND_BUSY: State.OK,
    AvailabilityStatus.UNAVAILABLE_AND_ON_REQUEST: State.WARN,
    AvailabilityStatus.UNAVAILABLE_BECAUSE_BROKEN: State.CRIT,
    AvailabilityStatus.UNKNOWN: State.UNKNOWN,
}

ALARM_MAP = {
    AlertStatus.NONE: State.OK,
    AlertStatus.NON_CRITICAL: State.WARN,
    AlertStatus.CRITICAL: State.CRIT,
}


def parse_printer_io(string_table: List[StringTable]) -> Section:
    parsed: Section = {}
    for line in string_table[0]:
        tray_index, name, descr, snmp_status_raw, capacity_unit, capacity_max, level = line[:7]
        snmp_status = int(snmp_status_raw) if snmp_status_raw else 0

        transitioning = bool(snmp_status & 64)
        offline = bool(snmp_status & 32)

        if snmp_status & 16:
            alert = AlertStatus.CRITICAL
        elif snmp_status & 8:
            alert = AlertStatus.NON_CRITICAL
        else:
            alert = AlertStatus.NONE

        availability = AvailabilityStatus(snmp_status % 8)

        if name == "unknown" or not name:
            name = descr if descr else tray_index.split(".")[-1]

        if capacity_unit != "":
            capacity_unit = " " + printer_io_units[capacity_unit]

        parsed[name] = Tray(
            tray_index,
            name,
            descr,
            PrinterStates(
                availability,
                alert,
                offline,
                transitioning,
            ),
            capacity_unit,
            int(capacity_max) if capacity_max else 0,
            int(level) if level else 0,
        )

    return parsed


register.snmp_section(
    name="printer_input",
    detect=DETECT_PRINTER,
    parse_function=parse_printer_io,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.43.8.2.1",
            oids=[
                OIDEnd(),
                "13",  # Printer-MIB::prtInputName
                "18",  # Printer-MIB::prtInputDescription
                "11",  # Printer-MIB::prtInputStatus
                "8",  # Printer-MIB::prtInputCapacityUnit
                "9",  # Printer-MIB::prtInputMaxCapacity
                "10",  # Printer-MIB::prtInputCurrentLevel
            ],
        ),
    ],
)

register.snmp_section(
    name="printer_output",
    detect=DETECT_PRINTER,
    parse_function=parse_printer_io,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.43.9.2.1",
            oids=[
                OIDEnd(),
                "7",  # Printer-MIB::prtOutputName
                "12",  # Printer-MIB::prtOutputDescription
                "6",  # Printer-MIB::prtOutputStatus
                "3",  # Printer-MIB::prtOutputCapacityUnit
                "4",  # Printer-MIB::prtOutputMaxCapacity
                "5",  # Printer-MIB::prtOutputRemainingCapacity
            ],
        ),
    ],
)


def discovery_printer_io(section: Section) -> DiscoveryResult:
    for tray in section.values():
        if tray.description == "":
            continue
        if tray.capacity_max == 0:  # useless
            continue
        if tray.states.availability in [
            AvailabilityStatus.UNAVAILABLE_BECAUSE_BROKEN,
            AvailabilityStatus.UNKNOWN,
        ]:
            continue
        yield Service(item=tray.name)


def check_printer_io(
    item: str, params: Mapping[str, Any], section: Section, io_type: IOType
) -> CheckResult:
    tray = section.get(item)
    if tray is None:
        return

    if tray.description:
        yield Result(state=State.OK, summary=tray.description)

    if tray.states.offline:
        yield Result(state=State.CRIT, summary="Offline")

    if tray.states.transitioning:
        yield Result(state=State.OK, summary="Transitioning")

    status = tray.states.availability.name.replace("_", " ").capitalize()
    yield Result(state=STATES_MAP[tray.states.availability], summary=f"Status: {status}")

    yield Result(
        state=ALARM_MAP[tray.states.alerts],
        summary=f"Alerts: {tray.states.alerts.value}",
    )

    if tray.level in [-1, -2] or tray.level < -3:
        return  # totally skip this info when level is unknown or not limited

    if tray.capacity_max in (-2, -1, 0):
        if tray.capacity_unit != " unknown":
            # -2: unknown, -1: no restriction, 0: due to saveint
            yield Result(
                state=State.OK, summary="Capacity: %s%s" % (tray.level, tray.capacity_unit)
            )
        return

    if tray.capacity_unit != " unknown":
        yield Result(
            state=State.OK, summary=f"Maximal capacity: {tray.capacity_max}{tray.capacity_unit}"
        )

    quantity_message = "remaining" if io_type == IOType.INPUT else "filled"

    if tray.level == -3:
        yield Result(state=State.OK, summary=f"At least one {quantity_message}")
        return

    yield from check_levels(
        100.0 * tray.level / tray.capacity_max,  # to percent
        levels_upper=None if io_type == IOType.INPUT else params["capacity_levels"],
        levels_lower=params["capacity_levels"] if io_type == IOType.INPUT else None,
        render_func=render.percent,
        label=quantity_message.capitalize(),
    )


def check_printer_input(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_printer_io(item, params, section, IOType.INPUT)


register.check_plugin(
    name="printer_input",
    service_name="Input %s",
    discovery_function=discovery_printer_io,
    check_function=check_printer_input,
    check_ruleset_name="printer_input",
    check_default_parameters={"capacity_levels": (0.0, 0.0)},
)


def check_printer_output(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_printer_io(item, params, section, IOType.OUTPUT)


register.check_plugin(
    name="printer_output",
    service_name="Output %s",
    discovery_function=discovery_printer_io,
    check_function=check_printer_output,
    check_ruleset_name="printer_output",
    check_default_parameters={"capacity_levels": (100.0, 100.0)},
)
