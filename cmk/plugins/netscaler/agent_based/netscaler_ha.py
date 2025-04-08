#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, StringTable

from .lib import SNMP_DETECT


@dataclass(frozen=True, kw_only=True)
class Section:
    peer_state: int
    current_status: int
    current_state: int


def parse_netscaler_ha(string_table: StringTable) -> Section | None:
    return (
        Section(
            peer_state=int(string_table[0][0]),
            current_status=int(string_table[0][1]),
            current_state=int(string_table[0][2]),
        )
        if string_table
        else None
    )


snmp_section_netscaler_ha = SimpleSNMPSection(
    name="netscaler_ha",
    parse_function=parse_netscaler_ha,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.23",
        oids=[
            "3",
            "23",
            "24",
        ],
    ),
    detect=SNMP_DETECT,
)
