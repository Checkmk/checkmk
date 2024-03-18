#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.cpu import Load, Section

from .lib import DETECT_PEAKFLOW_SP, DETECT_PEAKFLOW_TMS, DETECT_PRAVAIL


def parse_arbor_cpu_load(string_table: StringTable) -> Section | None:
    """
    >>> parse_arbor_cpu_load([["112", "156", "345"]])
    Section(load=Load(load1=1.12, load5=1.56, load15=3.45), num_cpus=1, threads=None, type=<ProcessorType.unspecified: 0>)
    """
    return (
        Section(
            load=Load(*(float(l) / 100 for l in string_table[0])),
            num_cpus=1,
        )
        if string_table
        else None
    )


snmp_section_arbor_provail_cpu_load = SimpleSNMPSection(
    name="arbor_pravail_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_arbor_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=[
            "3.0",  # deviceCpuLoadAvg1min
            "4.0",  # deviceCpuLoadAvg5min
            "5.0",  # deviceCpuLoadAvg15min
        ],
    ),
    detect=DETECT_PRAVAIL,
)


snmp_section_arbor_peakflow_tms_cpu_load = SimpleSNMPSection(
    name="arbor_peakflow_tms_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_arbor_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.2",
        oids=[
            "3.0",  # deviceCpuLoadAvg1min
            "4.0",  # deviceCpuLoadAvg5min
            "5.0",  # deviceCpuLoadAvg15min
        ],
    ),
    detect=DETECT_PEAKFLOW_TMS,
)


snmp_section_arbor_peakflow_sp_cpu_load = SimpleSNMPSection(
    name="arbor_peakflow_sp_cpu_load",
    parsed_section_name="cpu",
    parse_function=parse_arbor_cpu_load,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=[
            "1.0",  # deviceCpuLoadAvg1min
            "2.0",  # deviceCpuLoadAvg5min
            "3.0",  # deviceCpuLoadAvg15min
        ],
    ),
    detect=DETECT_PEAKFLOW_SP,
)
