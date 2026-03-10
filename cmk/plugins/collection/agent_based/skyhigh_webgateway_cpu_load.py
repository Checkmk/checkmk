#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Skyhigh Secure Web Gateway devices expose CPU load via UCD-SNMP-MIB OIDs,
but are not detected by the generic UCD detection rule. Adding them there
would also enable ucd_mem and other UCD-based sections unintentionally.
This section specifically targets Skyhigh devices for CPU load only.
"""

from collections.abc import Sequence

from cmk.agent_based.v2 import SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib import mcafee_gateway
from cmk.plugins.lib.cpu import Load, Section

_EXPECTED_CPU_LOAD_ENTRIES = 3


def parse_ucd_cpu_load(string_table: Sequence[StringTable]) -> Section | None:
    cpu_loads, cpu_count = string_table
    if len(cpu_loads) != _EXPECTED_CPU_LOAD_ENTRIES:
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


snmp_section_skyhigh_webgateway_cpu_load = SNMPSection(
    name="skyhigh_webgateway_cpu_load",
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
    detect=mcafee_gateway.DETECT_SKYHIGH_WEBGATEWAY,
)
