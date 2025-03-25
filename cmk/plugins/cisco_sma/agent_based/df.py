#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import (
    DfBlock,
    DfSection,
)

from .detect import DETECT_CISCO_SMA

_UNIT_TO_MB = {
    "kB": 10**-3,
    "MB": 10**0,
    "GB": 10**3,
    "TB": 10**6,
    "PB": 10**9,
}


def _parse_df(string_table: StringTable) -> DfSection | None:
    total_disk_size: float = 0.0
    available_disk_size: float = 0.0
    used_disk_space: float = 0.0

    if not string_table or not string_table[0]:
        return None

    line = string_table[0][0]

    for part in re.split(r",\s*", line):
        name, size, unit, *_ = part.split(" ")
        if name == "Total_disk_space:":
            total_disk_size = float(size) * _UNIT_TO_MB[unit]
        elif name == "Available_disk_space:":
            available_disk_size = float(size) * _UNIT_TO_MB[unit]
        elif name == "Used_disk_space:":
            used_disk_space = float(size) * _UNIT_TO_MB[unit]

    return (
        [
            DfBlock(
                device="",
                fs_type=None,
                size_mb=total_disk_size,
                avail_mb=available_disk_size,
                reserved_mb=used_disk_space,
                mountpoint="/",
                uuid=None,
            )
        ],
        [],
    )


snmp_section_disk_io_utilization = SimpleSNMPSection(
    parsed_section_name="df",
    name="cisco_sma_filesystem",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["27.0"],
    ),
    parse_function=_parse_df,
)
