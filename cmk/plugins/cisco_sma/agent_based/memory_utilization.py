#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .detect import DETECT_CISCO_SMA


def _parse_memory_percentage_used(string_table: StringTable) -> float | None:
    if not string_table or not string_table[0]:
        return None

    return float(string_table[0][0])


snmp_section_memory_utilization = SimpleSNMPSection(
    parsed_section_name="memory_utilization",
    name="cisco_sma_memory_utilization",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["1.0"],
    ),
    parse_function=_parse_memory_percentage_used,
    supersedes=["hr_mem"],
)
