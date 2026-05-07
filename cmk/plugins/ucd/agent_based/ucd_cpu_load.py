#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.cpu import Load, Section
from cmk.plugins.lib.ucd_hr_detection import UCD


def parse_ucd_cpu_load(string_table: Sequence[StringTable]) -> Section | None:
    cpu_loads, cpu_count = string_table
    if len(cpu_loads) != 3:
        return None
    return Section(
        load=Load(
            *(
                (
                    float(float_cpu_load_str.replace(",", "."))
                    if float_cpu_load_str
                    else float(int_cpu_load_str) / 100.0
                    if int_cpu_load_str
                    else 0
                )
                for int_cpu_load_str, float_cpu_load_str in cpu_loads
            )
        ),
        num_cpus=(
            len(cpu_count) if cpu_count else 1
        ),  # fallback to 1 if we don't get the number of cpu's from SNMP
    )


snmp_section_ucd_cpu_load = SNMPSection(
    name="ucd_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_ucd_cpu_load,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2021.10.1",
            oids=[
                "5",  # UCD-SNMP-MIB::laLoadInt       Int table
                "6",  # UCD-SNMP-MIB::laLoadFloat     Float table
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.25.3.3.1",
            oids=[
                "1",  # HOST-RESOURCES-V2-MIB::hrProcessorFrwID
            ],
        ),
    ],
    detect=UCD,
)
