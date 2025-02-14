#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.lib.ups import DETECT_UPS_GENERIC

from .agent_based_api.v1 import OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable


def _parse_value(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_ups_power(
    string_table: list[StringTable],
) -> dict[str, int]:
    section: dict[str, int] = {}
    for idx, power_str in string_table[0]:
        if (power := _parse_value(power_str)) is None:
            continue

        # Some "RPS SpA" systems are not RFC conform in this value.
        # The values can get negative but should never be.
        if power < 0:
            power *= -1

        section[idx] = power
    return section


register.snmp_section(
    name="ups_power",
    parsed_section_name="epower",
    detect=DETECT_UPS_GENERIC,
    parse_function=parse_ups_power,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.33.1.4.4.1",
            oids=[
                OIDEnd(),
                "4",  # power
            ],
        )
    ],
)
