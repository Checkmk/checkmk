#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import List

from .agent_based_api.v1 import all_of, equals, exists, OIDEnd, register, SNMPTree, type_defs
from .utils import interfaces


def parse_emc_vplex_if(string_table: List[type_defs.StringTable]) -> interfaces.Section:
    directors = {}
    for director, ip in string_table[0]:
        directors[ip] = director

    return [
        interfaces.Interface(
            index=str(idx + 1),
            descr=frontend_info[0],
            alias="%s %s" % (directors[frontend_info[3].rsplit(".", 1)[0]], frontend_info[0]),
            type="",
            oper_status="1",
            in_octets=int(frontend_info[1]),
            out_octets=int(frontend_info[2]),
        )
        for idx, frontend_info in enumerate(string_table[1] + string_table[2])
    ]


register.snmp_section(
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
    detect=all_of(
        equals(".1.3.6.1.2.1.1.1.0", ""),
        exists(".1.3.6.1.4.1.1139.21.2.2.8.1.*"),
    ),
    supersedes=["if", "if64"],
)
