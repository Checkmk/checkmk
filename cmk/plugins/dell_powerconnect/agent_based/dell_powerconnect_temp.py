#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, startswith, StringTable


def parse_dell_powerconnect_temp(string_table: StringTable) -> None | tuple[float | None, str]:
    try:
        temp_str, dev_status = string_table[0]
    except (IndexError, ValueError):
        return None
    try:
        temp = float(temp_str)
    except ValueError:
        temp = None
    return (
        temp,
        {
            "1": "OK",
            "2": "unavailable",
            "3": "non operational",
        }.get(dev_status, "unknown[%s]" % dev_status),
    )


snmp_section_dell_powerconnect_temp = SimpleSNMPSection(
    name="dell_powerconnect_temp",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.53.15.1",
        oids=["9", "10"],
    ),
    parse_function=parse_dell_powerconnect_temp,
)
