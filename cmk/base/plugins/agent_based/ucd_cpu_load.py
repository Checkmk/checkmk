#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu import Load, Section
from .utils.ucd_hr_detection import UCD


def parse_ucd_cpu_load(string_table: StringTable) -> Optional[Section]:
    if len(string_table) != 3:
        return None
    return Section(
        load=Load(
            *(
                float(float_cpu_load_str.replace(",", "."))
                if float_cpu_load_str
                else float(int_cpu_load_str) / 100.0
                if int_cpu_load_str
                else 0
                for int_cpu_load_str, float_cpu_load_str in string_table
            )
        ),
        num_cpus=1,
    )


register.snmp_section(
    name="ucd_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_ucd_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.10.1",
        oids=[
            "5",  # UCD-SNMP-MIB::laLoadInt       Int table
            "6",  # UCD-SNMP-MIB::laLoadFloat     Float table
        ],
    ),
    detect=UCD,
)
