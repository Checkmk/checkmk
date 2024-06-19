#!/usr/bin/env python3
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

import re
from typing import NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)

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

SPEC_LINE_REGEX = re.compile(
    r".*physical processor"  # "The physical processor"
    r"(?:.*?(\d+) cores?)?"  # Optional: "has 2 core(s)", capture number
    r".*?(\d+) virtual processors?.*?"  # " and 16 virtual processor(s) (0-15)"
)


def parse_solaris_psrinfo_virtual(string_table: StringTable) -> int:
    return len(string_table)


agent_section_solaris_psrinfo_virtual = AgentSection(
    name="solaris_psrinfo_virtual",
    parse_function=parse_solaris_psrinfo_virtual,
)


def parse_solaris_psrinfo_physical(string_table: StringTable) -> int:
    return int(string_table[0][0])


agent_section_solaris_psrinfo_physical = AgentSection(
    name="solaris_psrinfo_physical",
    parse_function=parse_solaris_psrinfo_physical,
)


class ProcessorInfo(NamedTuple):
    model: str
    maximum_speed: str
    cpus: int | None
    cores: int | None
    threads: int | None


def parse_solaris_psrinfo_verbose(string_table: StringTable) -> ProcessorInfo:
    r"""Parse the output of "psrinfo -pv"
    >>> test_section_1 = [line.split() for line in (
    ...     "The physical processor has 3 cores and 24 virtual processors (0-15,56-63)\n"
    ...     "  The core has 8 virtual processors (56-63)\n"
    ...     "  The core has 8 virtual processors (0-7)\n"
    ...     "  The core has 8 virtual processors (8-15)\n"
    ...     "    SPARC-S7 (chipid 0, clock 4267 MHz)\n"
    ...     "The physical processor has 1 core and 8 virtual processors (16-23)\n"
    ...     "  The core has 8 virtual processors (16-23)\n"
    ...     "    SPARC-S7 (chipid 0, clock 4267 MHz)\n"
    ... ).splitlines()]
    >>> assert parse_solaris_psrinfo_verbose(test_section_1) == ProcessorInfo(
    ...     model="SPARC-S7",
    ...     maximum_speed="4267 MHz",
    ...     cpus=2,
    ...     cores=4,
    ...     threads=32,
    ... )
    >>> test_section_2 = [line.split() for line in (
    ...     "The physical processor has 16 virtual processors (0-15)\n"
    ...     "  SPARC-T5 (chipid 0, clock 3600 MHz)\n"
    ... ).splitlines()]
    >>> assert parse_solaris_psrinfo_verbose(test_section_2) == ProcessorInfo(
    ...     model="SPARC-T5",
    ...     maximum_speed="3600 MHz",
    ...     cpus=1,
    ...     cores=None,
    ...     threads=16,
    ... )
    """
    model = string_table[-1][0]
    maximum_speed = f"{string_table[-1][-2]} {string_table[-1][-1].strip(')')}"

    table_lines = [" ".join(line).lower() for line in string_table]
    raw_matches = (SPEC_LINE_REGEX.match(line) for line in table_lines)
    cpu_matches = [line.groups() for line in raw_matches if line is not None]

    cpus = len(cpu_matches) or None
    cores = sum(int(match[0]) for match in cpu_matches if match[0] is not None) or None
    threads = sum(int(match[1]) for match in cpu_matches if match[1] is not None) or None

    return ProcessorInfo(
        model=model,
        maximum_speed=maximum_speed,
        cpus=cpus,
        cores=cores,
        threads=threads,
    )


agent_section_solaris_psrinfo = AgentSection(
    name="solaris_psrinfo",
    parsed_section_name="solaris_psrinfo_verbose",
    parse_function=parse_solaris_psrinfo_verbose,
)


class ParsedTable(NamedTuple):
    cpus: int | None
    cores: int | None


# Don't include info about threads.
# We have that information from "psrinfo" and we would have to do some
# delicate regex-matchings/calculations here
def parse_solaris_psrinfo_table(string_table: StringTable) -> ParsedTable:
    r"""Parse the output of "psrinfo -t"
    >>> test_section_1 = [line.split() for line in (
    ...     "socket: 0\n"
    ...     "  core: 0\n"
    ...     "    cpus: 56-63\n"
    ...     "  core: 1\n"
    ...     "    cpus: 0-7\n"
    ...     "  core: 2\n"
    ...     "    cpus: 8-15\n"
    ...     "socket: 1\n"
    ...     "  core: 3\n"
    ...     "    cpus: 16-23\n"
    ... ).splitlines()]
    >>> result = parse_solaris_psrinfo_table(test_section_1)
    >>> expected = ParsedTable(cpus=2, cores=4)
    >>> assert result == expected, f"expected {expected!r} - got {result!r}"
    >>> test_section_2 = [line.split() for line in (
    ...     "socket: 0\n"
    ...     "    cpus: 56-63\n"
    ...     "socket: 1\n"
    ...     "    cpus: 16-23\n"
    ... ).splitlines()]
    >>> result = parse_solaris_psrinfo_table(test_section_2)
    >>> expected = ParsedTable(cpus=2, cores=None)
    >>> assert result == expected, f"expected {expected!r} - got {result!r}"
    """
    cpus = len([line for line in string_table if line[0].lower().startswith("socket")])
    cores = len([line for line in string_table if line[0].lower().startswith("core")])

    return ParsedTable(
        cpus=cpus or None,
        cores=cores or None,
    )


agent_section_solaris_psrinfo_table = AgentSection(
    name="solaris_psrinfo_table",
    parse_function=parse_solaris_psrinfo_table,
)


def inventory_solaris_cpus(
    section_solaris_psrinfo_physical: int | None,
    section_solaris_psrinfo_virtual: int | None,
    section_solaris_psrinfo_verbose: ProcessorInfo | None,
    section_solaris_psrinfo_table: ParsedTable | None,
) -> InventoryResult:
    inventory_attributes: dict[str, int | str] = {}

    # cpus and threads are also (partly) available in section_solaris_psrinfo
    # and section_solaris_psrinfo_table, but these are more reliable
    if section_solaris_psrinfo_physical is not None:
        inventory_attributes["cpus"] = section_solaris_psrinfo_physical
    if section_solaris_psrinfo_virtual is not None:
        inventory_attributes["threads"] = section_solaris_psrinfo_virtual

    if (
        cores := _get_cores(
            section_solaris_psrinfo_verbose,
            section_solaris_psrinfo_table,
            section_solaris_psrinfo_virtual,
        )
    ) is not None:
        inventory_attributes["cores"] = cores

    if section_solaris_psrinfo_verbose is not None:
        inventory_attributes["model"] = section_solaris_psrinfo_verbose.model
        inventory_attributes["max_speed"] = section_solaris_psrinfo_verbose.maximum_speed

        # See comment above: But if do not already have cpus or threads we use these ones:
        if "cpus" not in inventory_attributes and section_solaris_psrinfo_verbose.cpus is not None:
            inventory_attributes["cpus"] = section_solaris_psrinfo_verbose.cpus

        if (
            "threads" not in inventory_attributes
            and section_solaris_psrinfo_verbose.threads is not None
        ):
            inventory_attributes["threads"] = section_solaris_psrinfo_verbose.threads

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=inventory_attributes,
    )


def _get_cores(
    processor_info: ProcessorInfo | None,
    parsed_table: ParsedTable | None,
    threads: int | None,
) -> int | None:
    # 1st try: Obtain cores from parsed "psrinfo -t" table
    if parsed_table is not None and parsed_table.cores is not None:
        return parsed_table.cores

    if processor_info is None:
        return None

    # 2nd try: Obtain cores from parsed "psrinfo -pv" text
    # Exit if section is not available at all (shouldn't happen)
    if processor_info.cores is not None:
        return processor_info.cores

    if threads is None:
        return None

    # Last resort if there's still no information about cores:
    # All "current" SPARC M, T, and S series processors have 8 threads per core,
    # so we do the math in that case
    if processor_info.model in KNOWN_PROCESSORS:
        if threads % 8 == 0:
            return threads // 8

    return None


inventory_plugin_solaris_cpus = InventoryPlugin(
    name="solaris_cpus",
    sections=[
        "solaris_psrinfo_physical",
        "solaris_psrinfo_virtual",
        "solaris_psrinfo_verbose",
        "solaris_psrinfo_table",
    ],
    inventory_function=inventory_solaris_cpus,
)
