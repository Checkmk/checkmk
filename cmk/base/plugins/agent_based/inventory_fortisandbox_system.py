#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence

from .agent_based_api.v1 import Attributes, register, SNMPTree
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.fortinet import DETECT_FORTISANDBOX

Section = Sequence[str]


def parse_fortisandbox_system(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortisandbox_system([["v2.52-build0340 (GA)"]])
    ['v2.52-build0340 (GA)']
    """
    return string_table[0] if string_table else None


register.snmp_section(
    name="fortisandbox_system",
    parse_function=parse_fortisandbox_system,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.1",
        oids=[
            "1",  # fsaSysVersion
        ],
    ),
    detect=DETECT_FORTISANDBOX,
)


def inventory_fortisandbox_system(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "Version": section[0],
        },
    )


register.inventory_plugin(
    name="fortisandbox_system",
    inventory_function=inventory_fortisandbox_system,
)
