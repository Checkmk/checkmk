#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=consider-using-in

import enum
from typing import Literal, Mapping, NamedTuple

from cmk.base.check_api import check_levels, get_percent_human_readable

printer_io_units = {
    '-1': 'unknown',
    "1": "other",
    '0': 'unknown',
    '2': 'unknown',  # defined by PrtCapacityUnitTC used in newer revs.
    '3': '1/10000 in',
    '4': 'micrometers',
    '8': 'sheets',
    '16': 'feet',
    '17': 'meters',
    '18': 'items',
    '19': 'percent',
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


class PrinterStates(NamedTuple):
    availability: AvailabilityStatus
    alerts: Literal[0, 1, 2]
    offline: bool
    transitioning: bool


class Tray(NamedTuple):
    index: str
    name: str
    description: str
    states: PrinterStates
    capacity_unit: str
    capacity_max: int
    level: int


Section = Mapping[str, Tray]

_STATES_MAP = {
    AvailabilityStatus.AVAILABLE_AND_IDLE: 0,
    AvailabilityStatus.AVAILABLE_AND_STANDBY: 0,
    AvailabilityStatus.AVAILABLE_AND_ACTIVE: 0,
    AvailabilityStatus.AVAILABLE_AND_BUSY: 0,
    AvailabilityStatus.UNAVAILABLE_AND_ON_REQUEST: 1,
    AvailabilityStatus.UNAVAILABLE_BECAUSE_BROKEN: 2,
    AvailabilityStatus.UNKNOWN: 3,
}


def parse_printer_io(info) -> Section:
    parsed: Section = {}
    for line in info:
        index, name, descr, snmp_status_raw, capacity_unit, capacity_max, level = line[:7]
        snmp_status_raw = int(snmp_status_raw) if snmp_status_raw else 0

        transitioning = bool(snmp_status_raw & 64)
        offline = bool(snmp_status_raw & 32)
        alert = 2 if (snmp_status_raw & 16) else bool(snmp_status_raw & 8)
        availability = AvailabilityStatus(snmp_status_raw % 8)

        if name == "unknown" or not name:
            name = descr if descr else index.split('.')[-1]

        if capacity_unit != '':
            capacity_unit = ' ' + printer_io_units[capacity_unit]

        parsed[name] = Tray(
            index,
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


def inventory_printer_io(parsed: Section):
    for tray in parsed.values():
        if tray.description == '':
            continue
        if tray.capacity_max == 0:  # useless
            continue
        if tray.states.availability in [
                AvailabilityStatus.UNAVAILABLE_BECAUSE_BROKEN,
                AvailabilityStatus.UNKNOWN,
        ]:
            continue
        yield (tray.name, {})


def check_printer_io(item, params, parsed: Section, what):
    tray = parsed.get(item)
    if tray is None:
        return

    yield 0, tray.description

    if tray.states.offline:
        yield 2, "Offline"

    if tray.states.transitioning:
        yield 0, "Transitioning"

    yield (
        _STATES_MAP[tray.states.availability],
        "Status: %s" % tray.states.availability.name.replace("_", " ").capitalize(),
    )
    yield (
        tray.states.alerts,
        "Alerts: %s" % ["None", "Non-Critical", "Critical"][tray.states.alerts],
    )

    if tray.level in [-1, -2] or tray.level < -3:
        return  # totally skip this info when level is unknown or not limited

    if tray.capacity_max in (-2, -1, 0):
        # -2: unknown, -1: no restriction, 0: due to saveint
        yield 0, 'Capacity: %s%s' % (tray.level, tray.capacity_unit)
        return

    yield 0, f"Maximal capacity: {tray.capacity_max}{tray.capacity_unit}"

    how = 'remaining' if what == 'input' else 'filled'

    if tray.level == -3:
        yield 0, f"At least one {how}"
        return

    yield check_levels(
        100.0 * tray.level / tray.capacity_max,  # to percent
        None,  # no metric
        # levels[0], levels[1]: warn/crit output (upper)
        # levels[3], levels[4]: warn/crit input (lower)
        ((None, None) if what == 'input' else ()) + params["capacity_levels"],
        infoname=how.capitalize(),
        human_readable_func=get_percent_human_readable,
    )
