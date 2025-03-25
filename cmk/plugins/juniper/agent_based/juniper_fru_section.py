#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Frus (Field replaceable units) can be
# - power supply
# - fan tray
# - uplink module
# - transceivers
#
# .1.3.6.1.4.1.2636.3.1.15.1.5.2.1.1.0 Power Supply: Power Supply 0 @ 0/0/* --> JUNIPER-MIB::jnxFruName.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.2.2.1.0 Power Supply: Power Supply 0 @ 1/0/* --> JUNIPER-MIB::jnxFruName.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.1.1.1 FAN: Fan 1 @ 0/0/0 --> JUNIPER-MIB::jnxFruName.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.1.1.2 FAN: Fan 2 @ 0/0/1 --> JUNIPER-MIB::jnxFruName.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.2.1.1 FAN: Fan 1 @ 1/0/0 --> JUNIPER-MIB::jnxFruName.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.2.1.2 FAN: Fan 2 @ 1/0/1 --> JUNIPER-MIB::jnxFruName.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.5.7.1.0.0 FPC: EX3300 48-Port @ 0/*/* --> JUNIPER-MIB::jnxFruName.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.7.2.0.0 FPC: EX3300 48-Port @ 1/*/* --> JUNIPER-MIB::jnxFruName.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.1.1.0 PIC: 48x 10/100/1000 Base-T @ 0/0/* --> JUNIPER-MIB::jnxFruName.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.1.2.0 PIC: 4x GE/XE SFP+ @ 0/1/* --> JUNIPER-MIB::jnxFruName.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.2.1.0 PIC: 48x 10/100/1000 Base-T @ 1/0/* --> JUNIPER-MIB::jnxFruName.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.2.2.0 PIC: 4x GE/XE SFP+ @ 1/1/* --> JUNIPER-MIB::jnxFruName.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.9.1.0.0 Routing Engine 0 --> JUNIPER-MIB::jnxFruName.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.9.2.0.0 Routing Engine 1 --> JUNIPER-MIB::jnxFruName.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.2.1.1.0 7 --> JUNIPER-MIB::jnxFruType.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.2.2.1.0 7 --> JUNIPER-MIB::jnxFruType.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.1.1.1 13 --> JUNIPER-MIB::jnxFruType.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.1.1.2 13 --> JUNIPER-MIB::jnxFruType.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.2.1.1 13 --> JUNIPER-MIB::jnxFruType.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.2.1.2 13 --> JUNIPER-MIB::jnxFruType.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.6.7.1.0.0 3 --> JUNIPER-MIB::jnxFruType.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.7.2.0.0 3 --> JUNIPER-MIB::jnxFruType.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.1.1.0 11 --> JUNIPER-MIB::jnxFruType.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.1.2.0 11 --> JUNIPER-MIB::jnxFruType.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.2.1.0 11 --> JUNIPER-MIB::jnxFruType.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.2.2.0 11 --> JUNIPER-MIB::jnxFruType.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.9.1.0.0 6 --> JUNIPER-MIB::jnxFruType.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.9.2.0.0 6 --> JUNIPER-MIB::jnxFruType.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.2.1.1.0 6 --> JUNIPER-MIB::jnxFruState.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.2.2.1.0 6 --> JUNIPER-MIB::jnxFruState.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.1.1.1 6 --> JUNIPER-MIB::jnxFruState.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.1.1.2 6 --> JUNIPER-MIB::jnxFruState.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.2.1.1 6 --> JUNIPER-MIB::jnxFruState.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.2.1.2 6 --> JUNIPER-MIB::jnxFruState.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.8.7.1.0.0 6 --> JUNIPER-MIB::jnxFruState.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.7.2.0.0 6 --> JUNIPER-MIB::jnxFruState.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.1.1.0 6 --> JUNIPER-MIB::jnxFruState.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.1.2.0 6 --> JUNIPER-MIB::jnxFruState.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.2.1.0 6 --> JUNIPER-MIB::jnxFruState.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.2.2.0 6 --> JUNIPER-MIB::jnxFruState.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.9.1.0.0 6 --> JUNIPER-MIB::jnxFruState.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.9.2.0.0 6 --> JUNIPER-MIB::jnxFruState.9.2.0.0

from collections.abc import Mapping

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.juniper import DETECT_JUNIPER


def parse_juniper_fru(string_table: StringTable) -> Mapping[str, Mapping[str, str]]:
    parsed = {}
    for fru_name, fru_type, fru_state in string_table:
        # jnxFruName is read-only, thus we can replace here
        # some auto-generated declarations
        name = (
            fru_name.replace("Power Supply: Power Supply ", "")
            .replace("FAN: Fan ", "")
            .replace("@ ", "")
            .replace("/*", "")
            .strip()
        )
        parsed[name] = {
            "fru_type": fru_type,
            "fru_state": fru_state,
        }
    return parsed


snmp_section_juniper_fru = SimpleSNMPSection(
    name="juniper_fru",
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.15.1",
        oids=["5", "6", "8"],
    ),
    parse_function=parse_juniper_fru,
)
