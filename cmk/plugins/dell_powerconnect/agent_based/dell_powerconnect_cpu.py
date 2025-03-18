#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    contains,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


def parse_dell_powerconnect_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_powerconnect_cpu = SimpleSNMPSection(
    name="dell_powerconnect_cpu",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.1",
        oids=["6", "7", "8", "9"],
    ),
    parse_function=parse_dell_powerconnect_cpu,
)
