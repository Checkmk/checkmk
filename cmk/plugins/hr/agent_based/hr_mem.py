#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from contextlib import suppress

from cmk.agent_based.v2 import SNMPSection, SNMPTree, StringTable
from cmk.plugins.lib import memory, ucd_hr_detection

PreParsed = dict[str, list[tuple[str, int, int]]]


def pre_parse_hr_mem(string_table: Sequence[StringTable]) -> PreParsed:
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

    def identify_map_type(hrtype_str: str) -> str | None:
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
            ".1.3.6.1.2.1.25.3.1.9": None,  # Ciena 5164 SAOS 10 just reports this value for all partitions
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


# The "Physical memory" hrStorageUsed value is normally interpreted as
# INCLUDING the reclaimable page cache (classic net-snmp / UCD, which reports
# "MemTotal - MemFree"). Checkmk therefore subtracts the "Cached memory" entry
# to obtain the real usage.
#
# ArubaOS-CX switches (HPE Aruba Networking) instead report the physical "used"
# value with the cache already excluded (modern net-snmp "MemAvailable"
# semantics), while still exposing a large "Cached memory" entry. There the
# cached memory can exceed the reported "used" value, and subtracting it would
# understate the usage or even push it below zero. The two cases cannot be told
# apart from the HOST-RESOURCES-MIB values alone (RFC 2790 defines no
# relationship between storage entries), so these devices are recognized by
# their sysObjectID, which lives under the Aruba (enterprise 47196) wired switch
# product arc, e.g. ...47196.4.1.1.1.100 (6300M) or ...4.1.1.1.309 (6200F).
_CACHE_EXCLUDED_FROM_USED_SYS_OBJECT_IDS: tuple[str, ...] = (
    ".1.3.6.1.4.1.47196.4.1.1.1.",  # ArubaOS-CX switches (SUP-29474)
)


def _reports_cache_excluded_from_used(system_info: StringTable) -> bool:
    """Whether the device's SNMP agent reports the physical memory usage with the
    page cache already excluded (so the cache must not be subtracted again)."""
    if not system_info or not system_info[0]:
        return False
    sys_object_id = system_info[0][0]
    return any(
        sys_object_id.startswith(prefix) for prefix in _CACHE_EXCLUDED_FROM_USED_SYS_OBJECT_IDS
    )


def aggregate_meminfo(parsed: PreParsed, *, subtract_cache: bool = True) -> memory.SectionMemUsed:
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

            if subtract_cache and descr == "cached memory" and used > 0:
                # Account for cached memory (this works at least for systems using
                # the UCD snmpd (such as Linux based applicances)
                # some devices report negative used cache values...
                meminfo["Cached"] += used

    return meminfo


def parse_hr_mem(string_table: Sequence[StringTable]) -> memory.SectionMemUsed | None:
    pre_parsed = pre_parse_hr_mem(string_table)

    # Do we find at least one entry concerning memory?
    # some device have zero (broken) values
    if not any(size > 0 for _, size, __ in pre_parsed.get("RAM", [])):
        return None

    system_info = string_table[1] if len(string_table) > 1 else []
    subtract_cache = not _reports_cache_excluded_from_used(system_info)

    section = aggregate_meminfo(pre_parsed, subtract_cache=subtract_cache)
    return section if section.get("MemTotal") else None


snmp_section_hr_mem = SNMPSection(
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
        SNMPTree(
            base=".1.3.6.1.2.1.1",
            oids=[
                "2.0",  # sysObjectID
            ],
        ),
    ],
    detect=ucd_hr_detection.USE_HR_MEM,
)
