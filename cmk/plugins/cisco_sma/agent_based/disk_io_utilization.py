#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .detect import DETECT_CISCO_SMA


def parse(string_table: StringTable) -> float | None:
    return float(string_table[0][0]) if string_table else None


snmp_section_disk_io_utilization = SimpleSNMPSection(
    parsed_section_name="disk_io_utilization",
    name="cisco_sma_disk_io_utilization",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["3.0"],
    ),
    parse_function=parse,
)
