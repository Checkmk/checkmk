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
from typing import Any, Mapping, MutableMapping, NamedTuple, NewType, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

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


def parse_fjdarye_disks(info) -> SectionFjdaryeDisk:  # type:ignore[no-untyped-def]
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


def discover_fjdarye_disks(section: SectionFjdaryeDisk):  # type:ignore[no-untyped-def]
    for disk in section.values():
        if disk.state_disk != "3":
            yield disk.disk_index, disk.state_description


def check_fjdarye_disks(  # type:ignore[no-untyped-def]
    item: str, params: Mapping[str, Any] | str, section: SectionFjdaryeDisk
):

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


class FjdaryeRlun(NamedTuple):
    rlun_index: str
    raw_string: str


def parse_fjdarye_rluns(info: StringTable) -> Mapping[str, FjdaryeRlun]:
    readable_rluns: MutableMapping[str, FjdaryeRlun] = {}

    for rlun_index, raw_string in info:
        readable_rluns[rlun_index] = FjdaryeRlun(rlun_index=rlun_index, raw_string=raw_string)

    return readable_rluns


def discover_fjdarye_rluns(section: Mapping[str, FjdaryeRlun]):
    for rlun in section.values():
        if rlun.raw_string[3] == "\xa0":  # non-breaking space (decimal 160)
            # The fourth byte needs to be "\xa0" for a RLUN to be present
            yield rlun.rlun_index, {}


FJDARYE_RLUNS_STATUS_MAPPING = {
    "\x08": (1, "RLUN is rebuilding"),  # Back Space (decimal 8)
    "\x07": (1, "RLUN copyback in progress"),  # Bell (decimal 7)
    "A": (1, "RLUN spare is in use"),  # (decimal 65)
    "B": (
        0,
        "RLUN is in RAID0 state",
    ),  # (decimal 66) - assumption that B is RAID0 state
    "\x00": (
        0,
        "RLUN is in normal state",
    ),  # Null char (decimal 0) - assumption that \x00 is normal state
}


def check_fjdarye_rluns(item: str, _no_param: Mapping, section: Mapping[str, FjdaryeRlun]):

    if (rlun := section.get(item)) is None:
        return

    if rlun.raw_string[3] != "\xa0":
        yield (2, "RLUN is not present")
        return

    yield FJDARYE_RLUNS_STATUS_MAPPING.get(
        rlun.raw_string[2],  # The result state and summary are dependent on the third byte
        (2, "RLUN in unknown state"),
    )


# .
FjdaryeDeviceStatus = NewType("FjdaryeDeviceStatus", str)


def parse_fjdarye_sum(info: StringTable) -> Optional[FjdaryeDeviceStatus]:

    for status in info:
        if len(status) == 1:
            return FjdaryeDeviceStatus(status[0])
    return None


def discover_fjdarye_sum(section: Optional[FjdaryeDeviceStatus]):
    if section:
        yield "0", {}


FJDARYE_SUM_STATUS = {
    "1": (2, "unknown"),
    "2": (2, "unused"),
    "3": (0, "ok"),
    "4": (1, "warning"),
    "5": (2, "failed"),
}


def check_fjdarye_sum(_item: str, _no_param, section: Optional[FjdaryeDeviceStatus]):
    if section is not None:
        state, state_desc = FJDARYE_SUM_STATUS.get(section, (3, "unknown"))
        yield state, f"Status: {state_desc}"
