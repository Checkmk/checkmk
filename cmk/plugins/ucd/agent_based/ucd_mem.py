#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from contextlib import suppress
from typing import Literal, NotRequired, TypedDict

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, StringTable
from cmk.plugins.lib import ucd_hr_detection

# .1.3.6.1.4.1.2021.4.2.0 swap      --> UCD-SNMP-MIB::memErrorName.0
# .1.3.6.1.4.1.2021.4.3.0 8388604   --> UCD-SNMP-MIB::MemTotalSwap.0
# .1.3.6.1.4.1.2021.4.4.0 8388604   --> UCD-SNMP-MIB::MemAvailSwap.0
# .1.3.6.1.4.1.2021.4.5.0 4003584   --> UCD-SNMP-MIB::MemTotalReal.0
# .1.3.6.1.4.1.2021.4.11.0 12233816 --> UCD-SNMP-MIB::MemTotalFree.0
# .1.3.6.1.4.1.2021.4.12.0 16000    --> UCD-SNMP-MIB::memMinimumSwap.0
# .1.3.6.1.4.1.2021.4.13.0 3163972  --> UCD-SNMP-MIB::memShared.0
# .1.3.6.1.4.1.2021.4.14.0 30364    --> UCD-SNMP-MIB::memBuffer.0
# .1.3.6.1.4.1.2021.4.15.0 10216780 --> UCD-SNMP-MIB::memCached.0
# .1.3.6.1.4.1.2021.4.100.0 0       --> UCD-SNMP-MIB::memSwapError.0
# .1.3.6.1.4.1.2021.4.101.0         --> UCD-SNMP-MIB::smemSwapErrorMsg.0


class Section(TypedDict):
    MemTotal: int
    MemAvail: int
    MemUsed: int
    SwapTotal: NotRequired[int]
    SwapFree: NotRequired[int]
    SwapUsed: NotRequired[int]
    MemFree: NotRequired[int]
    SwapMinimum: NotRequired[int]
    TotalTotal: NotRequired[int]
    TotalUsed: NotRequired[int]
    Shared: NotRequired[int]
    Buffer: NotRequired[int]
    Cached: NotRequired[int]
    error_swap: NotRequired[int]
    error: NotRequired[str]
    error_swap_msg: NotRequired[str]


# optional memory values
_OPTIONAL_KEYS: tuple[
    Literal[
        "SwapTotal",
        "SwapFree",
        "MemFree",
        "SwapMinimum",
        "Shared",
        "Buffer",
        "Cached",
    ],
    ...,
] = (
    "SwapTotal",
    "SwapFree",
    "MemFree",
    "SwapMinimum",
    "Shared",
    "Buffer",
    "Cached",
)


def _info_str_to_bytes(info_str: str) -> int:
    return int(info_str.replace("kB", "").strip()) * 1024


def parse_ucd_mem(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    row = string_table[0]

    # mandatory memory values
    try:
        mem_total = _info_str_to_bytes(row[0])
        mem_avail = _info_str_to_bytes(row[1])
    except (IndexError, ValueError):
        return None

    parsed = Section(
        MemTotal=mem_total,
        MemAvail=mem_avail,
        MemUsed=mem_total - mem_avail,  # might change below
    )
    for key, val in zip(_OPTIONAL_KEYS, row[2:-3]):
        try:
            parsed[key] = _info_str_to_bytes(val)
        except ValueError:
            pass

    # optional other values
    try:
        parsed["error_swap"] = int(row[-3])
    except ValueError:
        pass

    parsed["error"] = row[-2]
    parsed["error_swap_msg"] = row[-1]

    # Buffer and cache count as as free memory
    parsed["MemUsed"] -= parsed.get("Buffer", 0)
    parsed["MemUsed"] -= parsed.get("Cached", 0)

    with suppress(KeyError):
        parsed["SwapUsed"] = parsed["SwapTotal"] - parsed["SwapFree"]
    with suppress(KeyError):
        parsed["TotalTotal"] = parsed["MemTotal"] + parsed["SwapTotal"]
    with suppress(KeyError):
        parsed["TotalUsed"] = parsed["MemUsed"] - parsed["SwapUsed"]

    return parsed


snmp_section_ucd_mem = SimpleSNMPSection(
    name="ucd_mem",
    parse_function=parse_ucd_mem,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.4",
        oids=[
            "5",  # memTotalReal
            "6",  # memAvailReal
            "3",  # memTotalSwap
            "4",  # memAvailSwap
            "11",  # MemTotalFree
            "12",  # memMinimumSwap
            "13",  # memShared
            "14",  # memBuffer
            "15",  # memCached
            "100",  # memSwapError
            "2",  # memErrorName
            "101",  # smemSwapErrorMsg
        ],
    ),
    detect=ucd_hr_detection.USE_UCD_MEM,
)
