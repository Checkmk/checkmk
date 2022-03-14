#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import operator

from .agent_based_api.v1 import register, SNMPTree
from .utils import ucd_hr_detection

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


def _info_str_to_bytes(info_str):
    return int(info_str.replace("kB", "").strip()) * 1024


def parse_ucd_mem(string_table):
    info = string_table[0]

    # mandatory memory values
    try:
        parsed = {
            "MemTotal": _info_str_to_bytes(info[0][0]),
            "MemAvail": _info_str_to_bytes(info[0][1]),
        }
    except (IndexError, ValueError):
        return {}

    # optional memory values
    optional_keys_bytes = [
        "SwapTotal",
        "SwapFree",
        "MemFree",
        "SwapMinimum",
        "Shared",
        "Buffer",
        "Cached",
    ]
    for key, val in zip(optional_keys_bytes, info[0][2:-3]):
        try:
            parsed[key] = _info_str_to_bytes(val)
        except ValueError:
            pass

    # optional other values
    try:
        parsed["error_swap"] = int(info[0][-3])
    except ValueError:
        pass

    for key, val in zip(["error", "error_swap_msg"], info[0][-2:]):
        parsed[key] = val

    # additional memory values that need to be calculated
    parsed["MemUsed"] = parsed["MemTotal"] - parsed["MemAvail"]
    for key in ["Buffer", "Cached"]:
        try:
            parsed["MemUsed"] -= parsed[key]  # Buffer and cache count as as free memory
        except KeyError:
            pass

    for target_key, (source_key_1, source_key_2), oper in zip(
        ["SwapUsed", "TotalTotal", "TotalUsed"],
        [("SwapTotal", "SwapFree"), ("MemTotal", "SwapTotal"), ("MemUsed", "SwapUsed")],
        [operator.sub, operator.add, operator.sub],
    ):
        try:
            parsed[target_key] = oper(parsed[source_key_1], parsed[source_key_2])
        except KeyError:
            pass

    return parsed


register.snmp_section(
    name="ucd_mem",
    parse_function=parse_ucd_mem,
    fetch=[
        SNMPTree(
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
    ],
    detect=ucd_hr_detection.USE_UCD_MEM,
)
