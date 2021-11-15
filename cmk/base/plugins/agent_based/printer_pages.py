#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import List, Optional

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.printer import (
    check_printer_pages_types,
    DETECT_PRINTER_PAGES,
    discovery_printer_pages,
    Section,
)


def parse_printer_pages(string_table: List[StringTable]) -> Optional[Section]:
    """
    >>> parse_printer_pages([[['585']]])
    {'pages_total': 585}
    """
    return {"pages_total": int(string_table[0][0][0])} if string_table[0] else None


register.snmp_section(
    name="printer_pages",
    detect=DETECT_PRINTER_PAGES,
    parse_function=parse_printer_pages,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.43.10.2.1.4.1",
            oids=[
                "1",
            ],
        ),
    ],
)

register.check_plugin(
    name="printer_pages",
    service_name="Pages",
    discovery_function=discovery_printer_pages,
    check_function=check_printer_pages_types,
)
