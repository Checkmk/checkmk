#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional

from .agent_based_api.v1 import Attributes, register, SNMPTree
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, str]


def parse_fortimail_system(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortimail_system([["model 1a", "12345", "v5.4,build719,180328 (5.4.5 GA)"]])
    {'model': 'model 1a', 'serial': '12345', 'os': 'v5.4,build719,180328 (5.4.5 GA)'}
    """
    return (
        dict(
            zip(
                [
                    "model",
                    "serial",
                    "os",
                ],
                string_table[0],
            )
        )
        if string_table
        else None
    )


register.snmp_section(
    name="fortimail_system",
    parse_function=parse_fortimail_system,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "1",  # fmlSysModel
            "2",  # fmlSysSerial
            "3",  # fmlSysVersion
        ],
    ),
    detect=DETECT_FORTIMAIL,
)


def inventory_fortimail_system(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "model": section["model"],
            "serial": section["serial"],
        },
    )
    yield Attributes(
        path=["software", "operating_system"],
        inventory_attributes={
            "version": section["os"],
        },
    )


register.inventory_plugin(
    name="fortimail_system",
    inventory_function=inventory_fortimail_system,
)
