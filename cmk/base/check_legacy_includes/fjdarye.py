#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# pylint: disable=no-else-return

# check_mk plugin to monitor Fujitsu storage systems supporting FJDARY-E60.MIB or FJDARY-E100.MIB
# Copyright (c) 2012 FuH Entwicklungsgesellschaft mbH, Umkirch, Germany. All rights reserved.
# Author: Philipp Hoefflin, 2012, hoefflin+cmk@fuh-e.de

# generic data structure widely used in the FJDARY-Mibs:
# <oid>
# <oid>.1: Index
# <oid>.3: Status
# the latter can be one of the following:

from collections import Counter
from typing import Any, Mapping, MutableMapping, NamedTuple

fjdarye_item_status = {
    "1": (0, "Normal"),
    "2": (2, "Alarm"),
    "3": (1, "Warning"),
    "4": (2, "Invalid"),
    "5": (2, "Maintenance"),
    "6": (2, "Undefined"),
}


class FjdaryeItem(NamedTuple):
    item_index: str
    status: str


SectionFjdaryeItem = Mapping[str, FjdaryeItem]


def parse_fjdarye_item(info) -> SectionFjdaryeItem:
    fjdarye_items: MutableMapping[str, FjdaryeItem] = {}
    for item_index, status in info:
        fjdarye_items.setdefault(item_index, FjdaryeItem(item_index=item_index, status=status))
    return fjdarye_items


# generic inventory item - status other than 'invalid' is ok for inventory
def discover_fjdarye_item(section: SectionFjdaryeItem):
    for item in section.values():
        if item.status != "4":
            yield item.item_index, {}


# generic check_function returning the nagios-code and the status text
def check_fjdarye_item(item: str, _no_param, section: SectionFjdaryeItem):
    if fjdarye_item := section.get(item):
        yield fjdarye_item_status[fjdarye_item.status]


# .
#   .--single disks--------------------------------------------------------.
#   |               _             _            _ _     _                   |
#   |           ___(_)_ __   __ _| | ___    __| (_)___| | _____            |
#   |          / __| | '_ \ / _` | |/ _ \  / _` | / __| |/ / __|           |
#   |          \__ \ | | | | (_| | |  __/ | (_| | \__ \   <\__ \           |
#   |          |___/_|_| |_|\__, |_|\___|  \__,_|_|___/_|\_\___/           |
#   |                       |___/                                          |
#   +----------------------------------------------------------------------+
#   |                          disks main check                            |
#   '----------------------------------------------------------------------'


class FjdaryeDisk(NamedTuple):
    disk_index: str
    state: int
    state_description: str
    state_disk: str


SectionFjdaryeDisk = Mapping[str, FjdaryeDisk]

fjdarye_disks_status = {
    "1": (0, "available"),
    "2": (2, "broken"),
    "3": (1, "notavailable"),
    "4": (1, "notsupported"),
    "5": (0, "present"),
    "6": (1, "readying"),
    "7": (1, "recovering"),
    "64": (1, "partbroken"),
    "65": (1, "spare"),
    "66": (0, "formatting"),
    "67": (0, "unformated"),
    "68": (1, "notexist"),
    "69": (1, "copying"),
}


def parse_fjdarye_disks(info) -> SectionFjdaryeDisk:
    fjdarye_disks: MutableMapping[str, FjdaryeDisk] = {}

    for disk_index, disk_state in info:
        state, state_description = fjdarye_disks_status.get(
            disk_state,
            (3, "unknown[%s]" % disk_state),
        )
        fjdarye_disks.setdefault(
            disk_index,
            FjdaryeDisk(
                disk_index=disk_index,
                state=state,
                state_description=state_description,
                state_disk=disk_state,
            ),
        )
    return fjdarye_disks


def discover_fjdarye_disks(section: SectionFjdaryeDisk):
    for disk in section.values():
        if disk.state_disk != "3":
            yield disk.disk_index, disk.state_description


def check_fjdarye_disks(item: str, params: Mapping[str, Any] | str, section: SectionFjdaryeDisk):

    if (fjdarye_disk := section.get(item)) is None:
        return

    if isinstance(params, str):
        params = {"expected_state": params}
        # Determined at the time of discovery
        # "expected_state" can also be set as a parameter by the user

    if params.get("use_device_states") and fjdarye_disk.state > 0:
        yield fjdarye_disk.state, f"Status: {fjdarye_disk.state_description} (using device states)"
        return

    if (expected_state := params.get("expected_state")) and (
        expected_state != fjdarye_disk.state_description
    ):
        yield 2, f"Status: {fjdarye_disk.state_description} (expected: {expected_state})"
        return

    yield 0, f"Status: {fjdarye_disk.state_description}"


# .
#   .--summary disks-------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   |                            _ _     _                                 |
#   |                         __| (_)___| | _____                          |
#   |                        / _` | / __| |/ / __|                         |
#   |                       | (_| | \__ \   <\__ \                         |
#   |                        \__,_|_|___/_|\_\___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _fjdarye_disks_states_summary(section: SectionFjdaryeDisk) -> Mapping[str, int]:

    return Counter([disk.state_description for disk in section.values() if disk.state_disk != "3"])


def discover_fjdarye_disks_summary(section: SectionFjdaryeDisk):
    if current_disks_states := _fjdarye_disks_states_summary(section):
        yield None, current_disks_states


def _fjdarye_disks_printstates(states: Mapping[str, int]) -> str:
    """
    >>> _fjdarye_disks_printstates({"available": 4, "notavailable": 1})
    'Available: 4, Notavailable: 1'

    >>> _fjdarye_disks_printstates({})
    ''

    """
    return ", ".join([f"{s.title()}: {c}" for s, c in states.items()])


def check_fjdarye_disks_summary(
    _item: str, params: Mapping[str, int | bool], section: SectionFjdaryeDisk
):
    current_disk_states = _fjdarye_disks_states_summary(section)
    current_disks_states_text = _fjdarye_disks_printstates(current_disk_states)

    if params.get("use_device_states"):
        yield max(
            disk.state for disk in section.values()
        ), f"{current_disks_states_text} (using device states)"
        return

    expected_state = {k: v for k, v in params.items() if k != "use_device_states"}
    if current_disk_states == expected_state:
        yield 0, current_disks_states_text
        return

    summary = (
        f"{current_disks_states_text} (expected: {_fjdarye_disks_printstates(expected_state)})"
    )
    for expected_state_name, expected_state_count in expected_state.items():
        if current_disk_states.get(expected_state_name, 0) < expected_state_count:
            yield 2, summary
            return

    yield 1, summary


# .
#   .--rluns---------------------------------------------------------------.
#   |                            _                                         |
#   |                       _ __| |_   _ _ __  ___                         |
#   |                      | '__| | | | | '_ \/ __|                        |
#   |                      | |  | | |_| | | | \__ \                        |
#   |                      |_|  |_|\__,_|_| |_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_fjdarye_rluns(info):
    for line in info:
        rawdata = line[1]
        if rawdata[3] == "\xa0":  # RLUN is present
            yield line[0], "", None


def check_fjdarye_rluns(item, _no_params, info):
    for line in info:
        if item == line[0]:
            rawdata = line[1]
            if rawdata[3] != "\xa0":  # space
                return (2, "RLUN is not present")
            elif rawdata[2] == "\x08":  # backspace
                return (1, "RLUN is rebuilding")
            elif rawdata[2] == "\x07":  # ring terminal bell
                return (1, "RLUN copyback in progress")
            elif rawdata[2] == "\x41":  # A
                return (1, "RLUN spare is in use")
            elif rawdata[2] == "B":  # \x42
                return (0, "RLUN is in RAID0 state")  # assumption state 42
            elif rawdata[2] == "\x00":  # null byte
                return (0, "RLUN is in normal state")  # assumption
            return (2, "RLUN in unknown state %02x" % ord(rawdata[2]))
    return None


# .

fjdarye_sum_status = {1: "unknown", 2: "unused", 3: "ok", 4: "warning", 5: "failed"}


def inventory_fjdarye_sum(info):
    if len(info[0]) == 1:
        yield "0", {}


def check_fjdarye_sum(index, _no_param, info):
    for line in info:
        if len(info[0]) == 1:
            status = int(line[0])
            text = "Status is %s" % fjdarye_sum_status[status]

            if status == 3:
                return (0, "%s" % text)
            elif status == 4:
                return (1, "%s" % text)
            return (2, "%s" % text)

    return (3, "No status summary present")
