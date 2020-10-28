#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, Final, NamedTuple
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register, SNMPTree
from .utils.hp_proliant import MAP_TYPES_MEMORY, DETECT

_STATUS_MAP: Final = {
    '1': "other",
    '2': "notPresent",
    '3': "present",
    '4': "good",
    '5': "add",
    '6': "upgrade",
    '7': "missing",
    '8': "doesNotMatch",
    '9': "notSupported",
    '10': "badConfig",
    '11': "degraded",
    '12': "spare",
    '13': "partial",
}

_CONDITION_MAP: Final = {
    '1': 'other',
    '2': 'ok',
    '3': 'degraded',
    '4': 'degradedModuleIndexUnknown',
}


class Module(NamedTuple):
    number: str
    board: str
    cpu_num: int
    size: int
    typ: str
    serial: str
    status: str
    condition: str


Section = Dict[str, Module]


def parse_hp_proliant_mem(string_table: StringTable) -> Section:
    """
        >>> from pprint import pprint
        >>> pprint(parse_hp_proliant_mem([
        ...     ['0', '0', '1', '4194304', '15', '', '4', '2'],
        ...     ['8', '0', '2', '4194304', '15', '', '4', '2'],
        ...     ['3', '0', '1', '0',       '15', '', '2', '1'],
        ...     ['9', '0', '2', '0',       '15', '', '2', '1'],
        ... ]))
        {'0': Module(number='0', board='0', cpu_num=1, size=4294967296, typ='DIMM DDR3', serial='', status='good', condition='ok'),
         '3': Module(number='3', board='0', cpu_num=1, size=0, typ='DIMM DDR3', serial='', status='notPresent', condition='other'),
         '8': Module(number='8', board='0', cpu_num=2, size=4294967296, typ='DIMM DDR3', serial='', status='good', condition='ok'),
         '9': Module(number='9', board='0', cpu_num=2, size=0, typ='DIMM DDR3', serial='', status='notPresent', condition='other')}

    """
    section = {}
    for mod_num, board_num, cpu_num, size, typ, serial, status, condition in string_table:
        try:
            size_bytes = int(size) * 1024
        except ValueError:
            continue

        module = Module(
            number=mod_num,
            board=board_num,
            cpu_num=int(cpu_num),
            size=size_bytes,
            typ=MAP_TYPES_MEMORY.get(typ, f"unknown ({typ})"),
            serial=serial,
            status=_STATUS_MAP.get(status, f"unknown ({status})"),
            condition=_CONDITION_MAP.get(condition, f"unknown ({condition})"),
        )
        section[module.number] = module

    return section


register.snmp_section(
    name="hp_proliant_mem",
    parse_function=parse_hp_proliant_mem,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.14.13.1",
        oids=[
            "1",  # CPQHLTH-MIB::cpqHeResMem2Module
            "2",  # CPQHLTH-MIB::cpqHeResMem2BoardNum
            "3",  # CPQHLTH-MIB::cpqHeResMem2CpuNum
            "6",  # CPQHLTH-MIB::cpqHeResMem2ModuleSize
            "7",  # CPQHLTH-MIB::cpqHeResMem2ModuleType
            "12",  # CPQHLTH-MIB::cpqHeResMem2SerialNo
            "19",  # CPQHLTH-MIB::cpqHeResMem2ModuleStatus
            "20",  # CPQHLTH-MIB::cpqHeResMem2ModuleCondition
        ],
    ),
    detect=DETECT,
)
