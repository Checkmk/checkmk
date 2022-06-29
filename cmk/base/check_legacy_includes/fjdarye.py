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

from typing import Mapping, MutableMapping, NamedTuple, NewType, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

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
