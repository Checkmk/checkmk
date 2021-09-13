#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional

from .agent_based_api.v1 import Attributes, register, SNMPTree
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.fortinet import DETECT_FORTIAUTHENTICATOR

Section = Mapping[str, str]


def parse_fortiauthenticator_system(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortiauthenticator_system([['FACVM', 'FAC-VMTM18000123']])
    {'model': 'FACVM', 'serial': 'FAC-VMTM18000123'}
    """
    return (
        {
            "model": string_table[0][0],
            "serial": string_table[0][1],
        }
        if string_table
        else None
    )


register.snmp_section(
    name="fortiauthenticator_system",
    parse_function=parse_fortiauthenticator_system,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.113.1",
        oids=[
            "1",  # facSysModel
            "2",  # facSysSerial
        ],
    ),
    detect=DETECT_FORTIAUTHENTICATOR,
)


def inventory_fortiauthenticator_system(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "Model": section["model"],
            "Serial number": section["serial"],
        },
    )


register.inventory_plugin(
    name="fortiauthenticator_system",
    inventory_function=inventory_fortiauthenticator_system,
)
