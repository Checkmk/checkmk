#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 8 virtual processors (0-7)
#  SPARC64-VII+ (portid 1024 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (8-15)
#  SPARC64-VII+ (portid 1032 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (16-23)
#  SPARC64-VII+ (portid 1040 impl 0x7 ver 0xc1 clock 2660 MHz)
# The physical processor has 8 virtual processors (24-31)
#  SPARC64-VII+ (portid 1048 impl 0x7 ver 0xc1 clock 2660 MHz)

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 10 cores and 80 virtual processors (0-79)
#  The core has 8 virtual processors (0-7)
#  The core has 8 virtual processors (8-15)
#  The core has 8 virtual processors (16-23)
#  The core has 8 virtual processors (24-31)
#  The core has 8 virtual processors (32-39)
#  The core has 8 virtual processors (40-47)
#  The core has 8 virtual processors (48-55)
#  The core has 8 virtual processors (56-63)
#  The core has 8 virtual processors (64-71)
#  The core has 8 virtual processors (72-79)
#    SPARC-T5 (chipid 0, clock 3600 MHz)

# <<<solaris_psrinfo:persist(1405715354)>>>
# The physical processor has 8 virtual processors (0-7)
#  SPARC-T5 (chipid 0, clock 3600 MHz)

from typing import Optional, Union

from .agent_based_api.v1 import Attributes, regex, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

KNOWN_PROCESSORS = {
    "SPARC-M5",
    "SPARC-M6",
    "SPARC-M7",
    "SPARC-M8",
    "SPARC-T2",
    "SPARC-T3",
    "SPARC-T4",
    "SPARC-T5",
    "SPARC-S7",
}


def parse_solaris_psrinfo_virtual(string_table: StringTable) -> int:
    return len(string_table)


register.agent_section(
    name="solaris_psrinfo_virtual",
    parse_function=parse_solaris_psrinfo_virtual,
    supersedes=["solaris_prtpicl"],
)


def parse_solaris_psrinfo_physical(string_table: StringTable) -> int:
    return int(string_table[0][0])


register.agent_section(
    name="solaris_psrinfo_physical",
    parse_function=parse_solaris_psrinfo_physical,
    supersedes=["solaris_prtpicl"],
)


def inventory_solaris_psrinfo(section: StringTable) -> InventoryResult:
    # Backport from >=2.2:
    inventory_attributes: dict[str, Union[str, int]] = {
        "model": section[-1][0],
        "max_speed": f"{section[-1][-2]} {section[-1][-1].strip(')')}",
    }

    spec_line_regex = regex(
        r".*physical processor"  # "The physical processor"
        r"(?:.*?(\d+) cores?)?"  # Optional: "has 2 core(s)", capture number
        r".*?(\d+) virtual processors?.*?"  # " and 16 virtual processor(s) (0-15)"
    )

    table_lines = [" ".join(line).lower() for line in section]
    raw_matches = (spec_line_regex.match(line) for line in table_lines)
    cpu_matches = [line.groups() for line in raw_matches if line is not None]

    cpus = len(cpu_matches) or None
    cores = sum(int(match[0]) for match in cpu_matches if match[0] is not None) or None
    threads = sum(int(match[1]) for match in cpu_matches if match[1] is not None) or None

    if cpus is not None:
        inventory_attributes["cpus"] = cpus

    if cores is not None:
        inventory_attributes["cores"] = cores

    if threads is not None:
        inventory_attributes["threads"] = threads

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=inventory_attributes,
    )


register.inventory_plugin(
    name="solaris_psrinfo",
    inventory_function=inventory_solaris_psrinfo,
)


def inventory_solaris_cpus(
    section_solaris_psrinfo_physical: Optional[int],
    section_solaris_psrinfo_virtual: Optional[int],
    section_solaris_psrinfo: Optional[StringTable],
    section_solaris_psrinfo_table: Optional[StringTable],
) -> InventoryResult:
    if section_solaris_psrinfo_physical is None:
        return
    if section_solaris_psrinfo_virtual is None:
        return

    cpus = section_solaris_psrinfo_physical
    threads = section_solaris_psrinfo_virtual

    inventory_attributes = {
        "cpus": cpus,
        "threads": threads,
    }

    if (
        cores := _get_cores(
            section_solaris_psrinfo,
            section_solaris_psrinfo_table,
            threads,
        )
    ) > 0:
        inventory_attributes["cores"] = cores

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=inventory_attributes,
    )


def _get_cores(
    section_solaris_psrinfo: Optional[StringTable],
    section_solaris_psrinfo_table: Optional[StringTable],
    threads: int,
) -> int:
    try:
        if section_solaris_psrinfo_table is not None:
            cores = _cores_from_psrinfo_t(section_solaris_psrinfo_table)
        elif section_solaris_psrinfo is not None:
            cores = _cores_from_psrinfo_pv(
                section_solaris_psrinfo,
                threads,
            )
        else:
            cores = 0
    except Exception:
        # Just leave out the information about cores if something goes wrong
        return 0

    return cores


def _cores_from_psrinfo_t(section: StringTable) -> int:
    return len([line for line in section if line[0].lower().startswith("core")])


def _cores_from_psrinfo_pv(section: StringTable, threads: int) -> int:
    cores = 0

    # Parse the section for mentionings like "...the physical processor has 5 cores..."
    # or "...the physical processor has 1 core..."
    flat_table = [entry for line in section for entry in line]
    for index, entry in enumerate(flat_table):
        if "core" in entry.lower():
            cores += _try_int(flat_table[index - 1])

    if cores == 0:
        # Last resort if there's still no information about cores:
        # All "current" SPARC M, T, and S series processors have 8 threads per core,
        # so we do the math in that case
        if section[-1][0] in KNOWN_PROCESSORS:
            if threads % 8 == 0:
                cores = threads // 8

    return cores


def _try_int(i: str):
    try:
        return int(i)
    except ValueError:
        return 0


register.inventory_plugin(
    name="solaris_cpus",
    sections=[
        "solaris_psrinfo_physical",
        "solaris_psrinfo_virtual",
        "solaris_psrinfo",
        "solaris_psrinfo_table",
    ],
    inventory_function=inventory_solaris_cpus,
)


def inv_solaris_prtpicl(
    section_solaris_psrinfo_physical: Optional[int],
    section_solaris_psrinfo_virtual: Optional[int],
    section_solaris_prtpicl: Optional[StringTable],
) -> InventoryResult:
    if not (section_solaris_psrinfo_physical is None and section_solaris_psrinfo_virtual is None):
        return

    if section_solaris_prtpicl is None:
        return

    cmp_no = 0
    core_no = 0
    cpu_no = 0
    for line in section_solaris_prtpicl:
        if line[0] == "cmp":
            cmp_no += 1
        elif line[0] == "core":
            core_no += 1
        elif line[0] == "cpu":
            cpu_no += 1

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes={
            "cpus": cmp_no,
            "cores": core_no,
            "threads": cpu_no,
        },
    )


# Note: This check is deprecated since Checkmk 2.1 and will vanish with Checkmk 2.2.
# In Checkmk 2.1, it will only be used if the old prtpicl section is there, while the new
# sections solaris_psrinfo_physical and solaris_psrinfo_virtual are missing.
register.inventory_plugin(
    name="solaris_prtpicl",
    sections=[
        "solaris_psrinfo_physical",
        "solaris_psrinfo_virtual",
        "solaris_prtpicl",
    ],
    inventory_function=inv_solaris_prtpicl,
)
