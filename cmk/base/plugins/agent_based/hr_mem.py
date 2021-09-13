#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import suppress
from typing import Dict, List, Optional, Tuple

from .agent_based_api.v1 import register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable
from .utils import memory, ucd_hr_detection

PreParsed = Dict[str, List[Tuple[str, int, int]]]


def pre_parse_hr_mem(string_table: List[StringTable]) -> PreParsed:
    """
    >>> for item, values in pre_parse_hr_mem([[
    ...     ['.1.3.6.1.2.1.25.2.1.2', 'Physical memory', '4096', '11956593', '11597830'],
    ...     ['.1.3.6.1.2.1.25.2.1.2', 'Real memory', '4096', '181626', '381'],
    ...     ['.1.3.6.1.2.1.25.2.1.3', 'Virtual memory', '4096', '807034', '1604'],
    ... ]]).items():
    ...   print(item, values)
    RAM [('physical memory', 48974204928, 47504711680), ('real memory', 743940096, 1560576)]
    virtual memory [('virtual memory', 3305611264, 6569984)]
    """
    info = string_table[0]

    def identify_map_type(hrtype_str: str) -> Optional[str]:
        map_types = {
            ".1.3.6.1.2.1.25.2.1.1": "other",
            ".1.3.6.1.2.1.25.2.1.2": "RAM",
            ".1.3.6.1.2.1.25.2.1.3": "virtual memory",
            ".1.3.6.1.2.1.25.2.1.4": "fixed disk",
            ".1.3.6.1.2.1.25.2.1.5": "removeable disk",
            ".1.3.6.1.2.1.25.2.1.6": "floppy disk",
            ".1.3.6.1.2.1.25.2.1.7": "compact disk",
            ".1.3.6.1.2.1.25.2.1.8": "RAM disk",
            ".1.3.6.1.2.1.25.2.1.9": "flash memory",
            ".1.3.6.1.2.1.25.2.1.10": "network disk",
            # known misbehaving devices returning rubbish for `hrStorageType`
            # HP and OKI seem to be unable to write '.1.3.6.1.2.1.25.2.1.2'
            ".1.3.6.1.2.1.25.2.1.20": "RAM",  # HP ProLiant DL380 G5
            "iso.3.6.1.2.1.25.2.1.2": "RAM",  # OKI 8300e bug
            ".0.1.3.6.1.2.1.25.2.1": "RAM",  # HP bug
            ".2.3848679438.841888046.842346034.774975026": "RAM",  # HP Officejet Pro 8600 N911g
            # Some devices don't care about proper SNMP at all but are known to not write
            # interesting data anyway so we can ignore them silently by returning None (rather
            # than "unknown")
            ".1.3.6.1.2.1.25.3.9": None,  # not relevant, contains info about file systems
            ".0.0": None,  # Arris modems set ".0.0"
            "": None,  # ClearPass Policy Manager doesn't even send a type..
        }

        with suppress(KeyError):
            return map_types[hrtype_str]

        with suppress(KeyError):
            # split last OID digit in order to identify
            # '.1.3.6.1.2.1.25.3.9.*'
            return map_types[hrtype_str[: hrtype_str.rfind(".")]]

        raise KeyError(
            f"{hrtype_str} is not a valid value for hrStorageType. This is an indicator"
            " for invalid SNMP data sent by the host. Please provide a report for this"
            " incident to enable proper handling in the future."
        )

    def to_bytes(units: str) -> int:
        """In some cases instead of a plain byte-count an extra quantifier is appended
        e.g. '4096 Bytes' instead of just '4096'"""
        components = units.split(" ", 1)
        factor = 1 if len(components) == 1 or components[1] != "KBytes" else 1024
        return int(components[0]) * factor

    parsed: PreParsed = {}
    for hrtype, hrdescr, hrunits, hrsize, hrused in info:
        # should crash when the hrtype is not defined in the mapping table:
        # it may mean there was an important change in the way the OIDs are
        # mapped that we should know about
        map_type = identify_map_type(hrtype)

        # if hrStorageType maps to None it means the corresponding value is invalid - skip it
        if map_type is None:
            continue

        # Sometimes one of the values that is being converted is an empty
        # string. This means that SNMP delivers invalid data, and the service
        # should not be discovered.
        with suppress(ValueError):
            units = to_bytes(hrunits)
            size = int(hrsize) * units
            used = int(hrused) * units
            parsed.setdefault(map_type, []).append((hrdescr.lower(), size, used))

    return parsed


def aggregate_meminfo(parsed: PreParsed) -> memory.SectionMemUsed:
    """return a meminfo dict as expected by check_memory from mem.include"""
    meminfo: memory.SectionMemUsed = {"Cached": 0}

    for type_readable, entries in parsed.items():
        for descr, size, used in entries:
            if type_readable in ["RAM", "virtual memory"] and descr != "virtual memory":
                # We use only the first entry of each type. We have
                # seen devices (pfSense), that have lots of additional
                # entries that are not useful.
                if type_readable == "RAM":
                    meminfo.setdefault("MemTotal", size)
                    meminfo.setdefault("MemFree", (size - used))
                else:
                    # Strictly speaking, swap space is a part of the hard
                    # disk drive that is used for virtual memory.
                    # We use the name "Swap" here for consistency.
                    meminfo.setdefault("SwapTotal", size)
                    meminfo.setdefault("SwapFree", (size - used))

            if descr == "cached memory" and used > 0:
                # Account for cached memory (this works at least for systems using
                # the UCD snmpd (such as Linux based applicances)
                # some devices report negative used cache values...
                meminfo["Cached"] += used

    return meminfo


def parse_hr_mem(string_table: List[StringTable]) -> Optional[memory.SectionMemUsed]:
    pre_parsed = pre_parse_hr_mem(string_table)

    # Do we find at least one entry concerning memory?
    # some device have zero (broken) values
    if not any(size > 0 for _, size, __ in pre_parsed.get("RAM", [])):
        return None

    section = aggregate_meminfo(pre_parsed)
    return section if section.get("MemTotal") else None


register.snmp_section(
    name="hr_mem",
    parsed_section_name="mem_used",
    parse_function=parse_hr_mem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.25.2.3.1",
            oids=[
                "2",  # hrStorageType
                "3",  # hrStorageDescr
                "4",  # hrStorageAllocationUnits
                "5",  # hrStorageSize
                "6",  # hrStorageUsed
            ],
        ),
    ],
    detect=ucd_hr_detection.USE_HR_MEM,
)
