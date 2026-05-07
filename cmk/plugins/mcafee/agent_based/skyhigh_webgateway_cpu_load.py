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

from cmk.agent_based.v2 import SNMPSection, SNMPTree
from cmk.plugins.collection.agent_based.ucd_cpu_load import parse_ucd_cpu_load
from cmk.plugins.mcafee.libgateway import DETECT_SKYHIGH_WEBGATEWAY

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
    detect=DETECT_SKYHIGH_WEBGATEWAY,
)
