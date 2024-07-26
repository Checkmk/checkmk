#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

from cmk.agent_based.v2 import any_of, contains, State

MAP_TYPES_MEMORY: Final = {
    "1": "other",
    "2": "board",
    "3": "cpqSingleWidthModule",
    "4": "cpqDoubleWidthModule",
    "5": "simm",
    "6": "pcmcia",
    "7": "compaq-specific",
    "8": "DIMM",
    "9": "smallOutlineDimm",
    "10": "RIMM",
    "11": "SRIMM",
    "12": "FB-DIMM",
    "13": "DIMM DDR",
    "14": "DIMM DDR2",
    "15": "DIMM DDR3",
    "16": "DIMM FBD2",
    "17": "FB-DIMM DDR2",
    "18": "FB-DIMM DDR3",
}

PRODUCT_NAME_OID = ".1.3.6.1.4.1.232.2.2.4.2.0"

DETECT = any_of(
    contains(PRODUCT_NAME_OID, "proliant"),
    contains(PRODUCT_NAME_OID, "storeeasy"),
    contains(PRODUCT_NAME_OID, "synergy"),
)


STATUS_MAP = {
    "unknown": State.UNKNOWN,
    "other": State.UNKNOWN,
    "ok": State.OK,
    "degraded": State.CRIT,
    "failed": State.CRIT,
    "disabled": State.WARN,
}


def sanitize_item(item: str) -> str:
    r"""Sanitize null byte in item

    We observed some devices to send "\x00" (null-byte) as their name.
    Not all components delt well with it, so we replace it here
    with r"\x00" (literal backslash-x-zero-zero).
    As of Checkmk 2.3, this should in fact no longer be necessary.
    """
    return item.replace("\x00", r"\x00")
