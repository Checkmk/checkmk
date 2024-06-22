#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT


def parse_apc_symmetra_power(
    string_table: Sequence[StringTable],
) -> dict[str, int]:
    section: dict[str, int] = {}
    for phase_index, output_load_str in string_table[0]:
        output_load = int(output_load_str)
        if output_load in {0, -1}:
            continue
        section[phase_index] = output_load
    return section


snmp_section_apc_symmetra_power = SNMPSection(
    name="apc_symmetra_power",
    parsed_section_name="epower",
    detect=DETECT,
    parse_function=parse_apc_symmetra_power,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.318.1.1.1.9.3.3.1",
            oids=[
                "2.1",  # PowerNet-MIB::upsPhaseOutputPhaseIndex
                "7.1",  # PowerNet-MIB::upsPhaseOutputLoad
            ],
        )
    ],
)
