#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import OIDEnd, SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.emc import DETECT_VPLEX


def parse_emc_vplex_if(
    string_table: Sequence[StringTable],
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    directors = {}
    for director, ip in string_table[0]:
        directors[ip] = director

    return [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index=str(idx + 1),
                descr=frontend_info[0],
                alias="{} {}".format(
                    directors[frontend_info[3].rsplit(".", 1)[0]], frontend_info[0]
                ),
                type="",
                oper_status="1",
            ),
            interfaces.Counters(
                in_octets=int(frontend_info[1]),
                out_octets=int(frontend_info[2]),
            ),
        )
        for idx, frontend_info in enumerate(string_table[1] + string_table[2])
    ]


snmp_section_emc_vplex_if = SNMPSection(
    name="emc_vplex_if",
    parse_function=parse_emc_vplex_if,
    parsed_section_name="interfaces",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2",
            oids=[
                "1.1.3",  # vplexDirectorName
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2.5.1",
            oids=[
                "2",  # vplexDirectorFEPortName
                "9",  # vplexDirectorFEPortBytesRead
                "10",  # vplexDirectorFEPortBytesWrite
                OIDEnd(),
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1139.21.2.2.7.1",
            oids=[
                "2",  # vplexDirectorBEPortName
                "9",  # vplexDirectorBEPortBytesRead
                "10",  # vplexDirectorBEPortBytesWrite
                OIDEnd(),
            ],
        ),
    ],
    detect=DETECT_VPLEX,
    supersedes=["if", "if64"],
)
