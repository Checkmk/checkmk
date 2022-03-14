#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import List, Optional

from .agent_based_api.v1 import OIDEnd, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.printer import (
    check_printer_pages_types,
    DETECT_CANON_HAS_TOTAL,
    discovery_printer_pages,
    Section,
)

PAGE_CODES = {
    "301": "total",
    "112": "bw_a3",
    "113": "bw_a4",
    "122": "color_a3",
    "123": "color_a4",
    "106": "color",
    "109": "bw",
}


def parse_printer_pages_canon(string_table: List[StringTable]) -> Optional[Section]:
    """
    >>> parse_printer_pages_canon([[['1343', '123'], ['3464', '301'], ['122', '501']]])
    {'pages_color_a3': 501}
    """
    return {
        "pages_" + PAGE_CODES[name]: int(pages_text)
        for name, pages_text in string_table[0]
        if name in PAGE_CODES
    } or None


register.snmp_section(
    name="canon_pages",
    detect=DETECT_CANON_HAS_TOTAL,
    supersedes=["printer_pages"],
    parse_function=parse_printer_pages_canon,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1602.1.11.1.3.1",
            oids=[
                OIDEnd(),
                "4",
            ],
        ),
    ],
)

register.check_plugin(
    name="canon_pages",
    service_name="Pages",
    discovery_function=discovery_printer_pages,
    check_function=check_printer_pages_types,
)
