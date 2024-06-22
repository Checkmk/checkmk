#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import OIDEnd, SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.ups import DETECT_UPS_GENERIC


def _parse_value(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_ups_power(
    string_table: Sequence[StringTable],
) -> dict[str, int]:
    section: dict[str, int] = {}
    for idx, voltage_str, power_str in string_table[0]:
        if (voltage := _parse_value(voltage_str)) is None or not voltage:
            # TODO Fix unused voltage
            continue

        if (power := _parse_value(power_str)) is None:
            continue

        # Some "RPS SpA" systems are not RFC conform in this value.
        # The values can get negative but should never be.
        if power < 0:
            power *= -1

        section[idx] = power
    return section


snmp_section_ups_power = SNMPSection(
    name="ups_power",
    parsed_section_name="epower",
    detect=DETECT_UPS_GENERIC,
    parse_function=parse_ups_power,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.33.1.4.4.1",
            oids=[
                OIDEnd(),
                "2",  # voltage
                "4",  # power
            ],
        )
    ],
)
