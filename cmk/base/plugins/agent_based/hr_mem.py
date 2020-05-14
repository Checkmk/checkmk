#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, List, Tuple  # pylint: disable=unused-import
from cmk.base.plugins.agent_based.agent_based_api.v0 import register, SNMPTree
from cmk.base.plugins.agent_based.utils import ucd_hr_detection


def parse_hr_mem(string_table):
    info = string_table[0]

    map_types = {
        '.1.3.6.1.2.1.25.2.1.1': 'other',
        '.1.3.6.1.2.1.25.2.1.2': 'RAM',
        '.1.3.6.1.2.1.25.2.1.3': 'virtual memory',
        '.1.3.6.1.2.1.25.2.1.4': 'fixed disk',
        '.1.3.6.1.2.1.25.2.1.5': 'removeable disk',
        '.1.3.6.1.2.1.25.2.1.6': 'floppy disk',
        '.1.3.6.1.2.1.25.2.1.7': 'compact disk',
        '.1.3.6.1.2.1.25.2.1.8': 'RAM disk',
        '.1.3.6.1.2.1.25.2.1.9': 'flash memory',
        '.1.3.6.1.2.1.25.2.1.10': 'network disk',
    }

    def to_bytes(units):
        # type: (str) -> int
        """In some cases instead of a plain byte-count an extra quantifier is appended
        e.g. '4096 Bytes' instead of just '4096'"""
        components = units.split(" ", 1)
        factor = 1 if len(components) == 1 or components[1] != "KBytes" else 1024
        return int(components[0]) * factor

    parsed = {}  # type: Dict[str, List[Tuple[str, int, int]]]
    for hrtype, hrdescr, hrunits, hrsize, hrused in info:
        units = to_bytes(hrunits)
        size = int(hrsize) * units
        used = int(hrused) * units
        parsed.setdefault(map_types[hrtype], []).append((hrdescr.lower(), size, used))

    return parsed


register.snmp_section(
    name="hr_mem",
    parse_function=parse_hr_mem,
    trees=[
        SNMPTree(
            base=".1.3.6.1.2.1.25.2.3.1",
            oids=[
                '2',  # hrStorageType
                '3',  # hrStorageDescr
                '4',  # hrStorageAllocationUnits
                '5',  # hrStorageSize
                '6',  # hrStorageUsed
            ],
        ),
    ],
    detect=ucd_hr_detection.USE_HR_MEM,
)
